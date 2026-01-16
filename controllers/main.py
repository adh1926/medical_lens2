# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import logging
import traceback

_logger = logging.getLogger(__name__)

class MedicalLensController(http.Controller):

    # ---------------------------------------------------------
    # 1. دالة حساب السعر (محمية ضد الأخطاء)
    # ---------------------------------------------------------
    @http.route(['/shop/medical_lens/get_total_price'], type='json', auth="public", methods=['POST'], website=True)
    def get_medical_lens_price(self, template_id, right_values=None, left_values=None, qty=1):
        try:
            template = request.env['product.template'].browse(int(template_id))
            if not template.exists():
                return {'success': False, 'error': 'Product not found'}

            PTAV = request.env['product.template.attribute.value']
            
            # السعر الأساسي (احتياطي)
            base_price = template.list_price

            def _get_eye_price(val_ids):
                if not val_ids: return 0.0
                try:
                    clean_ids = [int(x) for x in val_ids if x]
                    if not clean_ids: return 0.0
                    
                    combination = PTAV.browse(clean_ids)
                    
                    # محاولة استخدام دالة أودوو الرسمية
                    res = template._get_combination_info(combination=combination, add_qty=float(qty))
                    return res.get('price', base_price)
                except Exception as e:
                    _logger.warning(f"Medical Price Calc Failed: {e}")
                    return base_price # العودة للسعر الأساسي في حال الخطأ

            total = 0.0
            if right_values: total += _get_eye_price(right_values)
            if left_values: total += _get_eye_price(left_values)

            # إذا لم يتم اختيار أي عين، نرجع 0
            if not right_values and not left_values:
                total = 0.0

            return {'success': True, 'total_price': total * float(qty)}

        except Exception as e:
            # لن نرجع خطأ يوقف الواجهة، بل نرجع 0
            _logger.error(f"Price Error: {e}")
            return {'success': True, 'total_price': 0.0}

    # ---------------------------------------------------------
    # 2. دالة الإضافة (محمية جداً - لن تنهار بسبب صورة أو وصف)
    # ---------------------------------------------------------
    @http.route(['/shop/medical_lens/add_cart'], type='json', auth="public", methods=['POST'], website=True)
    def add_medical_lens_to_cart(self, template_id, right_values=None, left_values=None, qty=1, 
                                 prescription_ref="", prescription_image=None, prescription_filename=None):
        try:
            order = request.website.sale_get_order(force_create=True)
            if not order: return {'success': False, 'error': 'Cart Error'}

            template = request.env['product.template'].browse(int(template_id))
            PTAV = request.env['product.template.attribute.value']
            last_line_id = False

            def _process_and_add(val_ids, eye_code, eye_label):
                nonlocal last_line_id
                clean_ids = [int(x) for x in val_ids if x]
                if not clean_ids: return False

                # 1. تجهيز البيانات
                all_values = PTAV.browse(clean_ids)
                variant_comb = request.env['product.template.attribute.value']
                no_variant_ids = []
                description_notes = []

                for val in all_values:
                    # القيم الديناميكية
                    if val.attribute_id.create_variant in ['always', 'dynamic']:
                        variant_comb += val
                    else:
                        no_variant_ids.append(val.id)
                        description_notes.append(f"{val.attribute_id.name}: {val.name}")

                # 2. إيجاد المنتج
                product_variant = False
                try:
                    if not variant_comb:
                        product_variant = template.product_variant_id
                    else:
                        product_variant = template._create_product_variant(variant_comb)
                    
                    if not product_variant:
                         info = template._get_combination_info(combination=variant_comb, add_qty=float(qty))
                         if info.get('product_id'):
                             product_variant = request.env['product.product'].browse(info['product_id'])
                except Exception as e:
                    raise Exception(f"Product Creation Failed: {str(e)}")

                if not product_variant:
                    raise Exception(f"Product not found for {eye_label}")

                # 3. محاولة نسخ الصورة (داخل try مستقل لكي لا يوقف العملية)
                if template.image_1920:
                    try:
                        if not product_variant.image_1920:
                            product_variant.sudo().write({'image_1920': template.image_1920})
                    except Exception as e:
                        _logger.warning(f"Image Copy Error (Ignored): {e}")

                # 4. الإضافة للسلة
                line_values = order._cart_update(
                    product_id=product_variant.id,
                    add_qty=float(qty)
                )
                
                # التحقق
                if line_values.get('quantity') == 0:
                     raise Exception(f"Stock Error: {eye_label} unavailable.")

                current_id = line_values.get('line_id')
                line = request.env['sale.order.line'].sudo().browse(current_id)

                # 5. فصل السطور
                if last_line_id and current_id == last_line_id:
                    new_line = line.copy({
                        'order_id': order.id,
                        'product_uom_qty': float(qty),
                        'medical_eye_side': eye_code
                    })
                    line.write({'product_uom_qty': line.product_uom_qty - float(qty)})
                    line = new_line
                    current_id = new_line.id
                
                last_line_id = current_id 

                # 6. تحديث الوصف (داخل try مستقل)
                try:
                    new_desc = f"{product_variant.display_name}\n*** {eye_label} ***"
                    if description_notes: new_desc += "\n" + " | ".join(description_notes)
                    if prescription_ref: new_desc += f"\n[Ref: {prescription_ref}]"
                    if prescription_image: new_desc += "\n[Imagen Adjunta]"

                    vals = {'medical_eye_side': eye_code, 'name': new_desc}
                    if prescription_ref: vals['medical_prescription_ref'] = prescription_ref
                    if no_variant_ids:
                        vals['product_no_variant_attribute_value_ids'] = [(6, 0, no_variant_ids)]
                    
                    # محاولة حفظ الصورة
                    if prescription_image:
                        vals['medical_prescription_image'] = prescription_image
                        vals['medical_prescription_fname'] = prescription_filename

                    line.write(vals)
                except Exception as e:
                    _logger.warning(f"Description Update Error (Ignored): {e}")

                return True

            # التنفيذ
            if right_values:
                _process_and_add(right_values, 'right', "OD (Derecho)")
            
            if left_values:
                _process_and_add(left_values, 'left', "OI (Izquierdo)")

            return {'success': True}

        except Exception as e:
            # طباعة الخطأ الكامل في السجل
            _logger.error(f"Medical Lens Fatal Error: {traceback.format_exc()}")
            return {'success': False, 'error': f"Server Error: {str(e)}"}
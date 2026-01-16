# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_medical_lens = fields.Boolean(string="Is Medical Lens", default=False)
    allow_prescription_upload = fields.Boolean(string="Permitir subir receta (Imagen)", default=True)
    medical_setup_type = fields.Selection([
        ('attribute', 'Productos Separados (Der/Izq son Atributos)'),
        ('ui_only', 'Producto Universal (Der/Izq son solo etiquetas)')
    ], string="Tipo de Configuración", default='attribute')

class ProductAttribute(models.Model):
    _inherit = 'product.attribute'
    is_medical_eye = fields.Boolean(string="Is Eye Attribute", default=False)

class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'
    medical_eye_side = fields.Selection([
        ('right', 'Ojo Derecho (OD)'),
        ('left', 'Ojo Izquierdo (OI)')
    ], string="Lado del Ojo")

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    medical_prescription_ref = fields.Char(string="Ref. Receta")
    medical_prescription_image = fields.Binary(string="Imagen Receta", attachment=True)
    medical_prescription_fname = fields.Char(string="Nombre Archivo")
    
    medical_eye_side = fields.Selection([
        ('right', 'OD (Derecho)'),
        ('left', 'OI (Izquierdo)')
    ], string="Lado del Ojo")

    # API Value (Calculated Field)
    api_value = fields.Float(string="Valor API", compute="_compute_api_value", store=True)

    @api.depends('product_id', 'product_no_variant_attribute_value_ids')
    def _compute_api_value(self):
        for line in self:
            sph = 0.0
            cyl = 0.0
            try:
                all_values = line.product_id.product_template_attribute_value_ids 
                if line.product_no_variant_attribute_value_ids:
                    all_values |= line.product_no_variant_attribute_value_ids
                
                for val in all_values:
                    attr_name = val.attribute_id.name.upper()
                    try:
                        clean_val = val.name.replace(',', '.').strip().replace('+', '')
                        number_val = float(clean_val)
                        if any(x in attr_name for x in ['SPH', 'ESFERA', 'ESF']):
                            sph = number_val
                        elif any(x in attr_name for x in ['CYL', 'CILINDRO', 'CIL']):
                            cyl = number_val
                    except ValueError:
                        continue
            except Exception:
                pass
            line.api_value = sph + cyl

    def _prepare_invoice_line(self, **optional_values):
        res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        res['medical_prescription_ref'] = self.medical_prescription_ref
        res['medical_prescription_image'] = self.medical_prescription_image
        res['medical_prescription_fname'] = self.medical_prescription_fname
        return res

    def action_show_image(self):
        self.ensure_one()
        return {
            'name': 'Imagen de Receta',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.line',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('medical_lens2.view_sale_line_image_popup').id,
            'target': 'new',
        }

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    medical_prescription_ref = fields.Char(string="Ref. Receta")
    medical_prescription_image = fields.Binary(string="Imagen Receta", attachment=True)
    medical_prescription_fname = fields.Char(string="Nombre Archivo")

    def action_show_image(self):
        self.ensure_one()
        return {
            'name': 'Imagen de Receta',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('medical_lens2.view_move_line_image_popup').id,
            'target': 'new',
        }
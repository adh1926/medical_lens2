# -*- coding: utf-8 -*-
from odoo import models, api

class MedicalLensMixin(models.AbstractModel):
    _name = 'medical.lens.mixin'
    _description = 'Helper methods for medical lens reports'

    def get_lens_details(self, line):
        if not line.product_id: return {}

        product = line.product_id
        eye_side = False
        
        # Priority to saved field, then name
        if hasattr(line, 'medical_eye_side') and line.medical_eye_side:
            eye_side = line.medical_eye_side
        elif any(x in (line.name or "") for x in ["Right", "(OD)", "Derecha", "Der"]):
            eye_side = 'right'
        elif any(x in (line.name or "") for x in ["Left", "(OS)", "Izquierda", "Izq"]):
            eye_side = 'left'
        
        if not eye_side:
            for val in product.product_template_attribute_value_ids:
                if val.attribute_id.is_medical_eye:
                    code = val.product_attribute_value_id.medical_eye_side
                    if code: eye_side = code
                    break

        attributes = {}
        # Combine variant and no_variant values
        all_values = product.product_template_attribute_value_ids 
        if hasattr(line, 'product_no_variant_attribute_value_ids'):
            all_values |= line.product_no_variant_attribute_value_ids

        # Mapping for Report
        keys_map = {
            'SPH': ['SPH', 'ESF', 'ESFERA', 'SPHERE'],
            'CYL': ['CYL', 'CIL', 'CILINDRO'],
            'AXIS': ['AXIS', 'AXE', 'EJE'],
            'ADD': ['ADD', 'ADI', 'ADICION']
        }

        for val in all_values:
            if val.attribute_id.is_medical_eye: continue
            attr_name = val.attribute_id.name.upper().strip()
            matched = False
            for std_key, keywords in keys_map.items():
                if any(k in attr_name for k in keywords):
                    attributes[std_key] = val.name
                    matched = True
                    break
            if not matched:
                attributes[attr_name] = val.name

        qty = line.product_uom_qty if hasattr(line, 'product_uom_qty') else line.quantity
        pres_ref = line.medical_prescription_ref or ""

        return {
            'side': eye_side,
            'attrs': attributes,
            'qty': qty,
            'product_name': product.name,
            'pres_ref': pres_ref
        }

class SaleOrder(models.Model):
    _inherit = ['sale.order', 'medical.lens.mixin']
    _name = 'sale.order'

class AccountMove(models.Model):
    _inherit = ['account.move', 'medical.lens.mixin']
    _name = 'account.move'
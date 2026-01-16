/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.MedicalLensApp = publicWidget.Widget.extend({
    selector: '#medical_lens_app',
    events: {
        'click #btn_add_medical_lens': '_onAddClick',
        'change .eye-checkbox': '_onEyeChange',
        'change select': '_onAttributeChange',
        'change input[name="add_qty"]': '_onAttributeChange',
        'keyup input[name="add_qty"]': '_onAttributeChange',
    },

    start: function() {
        this._updateButtonText();
        this._updatePrice();
        return this._super.apply(this, arguments);
    },

    _onEyeChange: function(ev) {
        const $target = $(ev.currentTarget);
        const section = $target.attr('id') === 'check_right' ? '.right-section' : '.left-section';
        if ($target.is(':checked')) {
            this.$(section).removeClass('section-disabled');
            this.$(section).find('select').prop('disabled', false);
        } else {
            this.$(section).addClass('section-disabled');
            this.$(section).find('select').prop('disabled', true);
        }
        this._updateButtonText();
        this._updatePrice();
    },

    _onAttributeChange: function() { this._updatePrice(); },

    _updateButtonText: function() {
        const r = this.$('#check_right').is(':checked');
        const l = this.$('#check_left').is(':checked');
        const $btn = this.$('#add_btn_text');
        if (r && l) $btn.text("Añadir Ambos Lentes");
        else if (r) $btn.text("Añadir Lente Derecho (OD)");
        else if (l) $btn.text("Añadir Lente Izquierdo (OI)");
        else $btn.text("Seleccione un lente");
    },

    _getSectionIds: function(sectionClass) {
        let ids = [];
        this.$(sectionClass + ' select:enabled').each((i, el) => {
            const val = parseInt($(el).val());
            if(val) ids.push(val);
        });
        const eyeVal = parseInt(this.$(sectionClass).data('eye-val-id'));
        if(eyeVal > 0) ids.push(eyeVal);
        return ids;
    },

    async _updatePrice() {
        const $priceContainer = this.$('#medical_lens_total_price');
        const $loading = this.$('#price_loading');
        $priceContainer.css('opacity', '0.5'); $loading.removeClass('d-none');
        
        const useRight = this.$('#check_right').is(':checked');
        const useLeft = this.$('#check_left').is(':checked');
        const tmplId = parseInt(this.$('#medical_tmpl_id').val());
        let qty = parseFloat($('input[name="add_qty"]').val()) || 1;

        const rightValues = useRight ? this._getSectionIds('.right-section') : null;
        const leftValues = useLeft ? this._getSectionIds('.left-section') : null;

        try {
            const result = await jsonrpc('/shop/medical_lens/get_total_price', {
                template_id: tmplId, right_values: rightValues, left_values: leftValues, qty: qty
            });
            
            // حتى لو فشل الحساب، نظهر 0.00 بدلاً من ---
            if (result.success) {
                $priceContainer.find('.price_val').text(result.total_price.toFixed(2));
            } else {
                console.warn("Price calc failed:", result.error);
                $priceContainer.find('.price_val').text("0.00");
            }
        } catch (e) {
            console.error(e);
            $priceContainer.find('.price_val').text("0.00");
        } finally {
            $priceContainer.css('opacity', '1');
            $loading.addClass('d-none');
        }
    },

    _readFile: function(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result.split(',')[1]);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    },

    async _onAddClick(ev) {
        ev.preventDefault();
        const $btn = $(ev.currentTarget);
        const useRight = this.$('#check_right').is(':checked');
        const useLeft = this.$('#check_left').is(':checked');

        if (!useRight && !useLeft) { alert("Por favor seleccione al menos un ojo."); return; }

        let qty = parseFloat($('input[name="add_qty"]').val()) || 1;
        const presRef = this.$('#prescription_ref').val() || "";
        let fileData = null;
        let fileName = null;
        const $fileInput = this.$('#prescription_file');
        if ($fileInput.length > 0 && $fileInput[0].files.length > 0) {
            const file = $fileInput[0].files[0];
            fileName = file.name;
            try { fileData = await this._readFile(file); } catch (err) { alert("Error leyendo archivo."); return; }
        }

        $btn.closest('button').addClass('disabled').text('Procesando...');
        const tmplId = parseInt(this.$('#medical_tmpl_id').val());
        const rightValues = useRight ? this._getSectionIds('.right-section') : null;
        const leftValues = useLeft ? this._getSectionIds('.left-section') : null;

        try {
            const result = await jsonrpc('/shop/medical_lens/add_cart', {
                template_id: tmplId, right_values: rightValues, left_values: leftValues, qty: qty,
                prescription_ref: presRef, prescription_image: fileData, prescription_filename: fileName
            });

            if (result.success) {
                // Success
                $btn.closest('button').removeClass('disabled').text('Añadir Seleccionados al Carrito');
                const modalEl = document.getElementById('medicalSuccessModal');
                if (window.bootstrap) { const m = new window.bootstrap.Modal(modalEl); m.show(); }
                else { window.location.href = "/shop/cart"; }
            } else {
                // Error - Show real error
                alert("Error: " + result.error);
                $btn.closest('button').removeClass('disabled').text('Intentar de nuevo');
            }
        } catch (e) {
            console.error(e);
            let msg = e.message || e.data?.message || "Error desconocido";
            alert("⚠️ Error del sistema:\n" + msg);
            $btn.closest('button').removeClass('disabled').text('Intentar de nuevo');
        }
    }
});
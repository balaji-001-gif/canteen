frappe.pages["canteen-pos"].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Canteen POS",
        single_column: true,
    });

    new CanteenPOS(page);
};

class CanteenPOS {
    constructor(page) {
        this.page = page;
        this.$body = page.$body;
        this.cart = [];
        this.all_items = [];
        this.selected_category = null;
        this.settings = {};
        this.payment_modes = [];
        this.make();
    }

    make() {
        // HTML template already provides the full layout
        // Just wire up events and load data
        this.setup_events();
        this.load_pos_data();
    }

    setup_events() {
        const me = this;

        // Search
        this.$body.find("#item-search").on("input", function () {
            me.filter_items($(this).val());
        });

        // Pay
        this.$body.find("#btn-pay").on("click", function () {
            me.process_payment();
        });

        // Clear
        this.$body.find("#btn-clear").on("click", function () {
            me.cart = [];
            me.render_cart();
            me.$body.find("#customer-name").val("");
            me.$body.find("#employee-field").val("").closest(".employee-row").hide();
            me.$body.find("#paid-amount").val("");
            me.$body.find("#change-display").hide();
            me.$body.find("#btn-pay").prop("disabled", true);
        });

        // Category filter
        this.$body.on("click", ".cat-btn", function () {
            me.$body.find(".cat-btn").removeClass("active");
            $(this).addClass("active");
            me.selected_category = $(this).data("cat") || null;
            me.filter_items(me.$body.find("#item-search").val());
        });

        // Item grid click (delegated) — lookup by item_code
        this.$body.on("click", ".item-card:not(.no-results)", function () {
            var itemCode = $(this).data("item");
            if (itemCode && me.all_items && me.all_items.length) {
                var item = me.all_items.find(function (i) {
                    return i.item_code === itemCode;
                });
                if (item) me.add_to_cart(item);
            }
        });

        // Cart quantity buttons (delegated)
        this.$body.on("click", ".ci-btn", function () {
            var idx = parseInt($(this).attr("data-idx"));
            if (isNaN(idx) || !me.cart[idx]) return;
            if ($(this).hasClass("qty-inc")) {
                me.cart[idx].quantity += 1;
            } else if ($(this).hasClass("qty-dec")) {
                me.cart[idx].quantity -= 1;
                if (me.cart[idx].quantity <= 0) {
                    me.cart.splice(idx, 1);
                }
            } else if ($(this).hasClass("remove-item")) {
                me.cart.splice(idx, 1);
            }
            me.render_cart();
        });

        // Payment mode change — toggle employee field
        this.$body.find("#payment-mode").on("change", function () {
            if ($(this).val() === "Wallet") {
                me.$body.find(".employee-row").show();
            } else {
                me.$body.find(".employee-row").hide();
            }
        });

        // Paid amount — show change
        this.$body.find("#paid-amount").on("input", function () {
            me.show_change();
        });

        // Receipt modal close
        this.$body.find("#receipt-close").on("click", function () {
            me.$body.find("#receipt-modal").removeClass("active");
        });

        // Close modal on overlay click
        this.$body.find("#receipt-modal").on("click", function (e) {
            if ($(e.target).is(".pos-modal-overlay")) {
                $(this).removeClass("active");
            }
        });
    }

    load_pos_data() {
        const me = this;
        this.show_loading(true);

        frappe.call({
            method: "canteen_management.api.pos_data",
            callback: function (r) {
                me.show_loading(false);
                if (r.message) {
                    var data = r.message;
                    me.settings = data.settings || {};
                    me.payment_modes = data.payment_modes || [];

                    me.render_categories(data.categories || []);
                    me.all_items = data.items || [];
                    me.render_items(me.all_items);
                    me.setup_payment_modes();
                }
            },
            error: function () {
                me.show_loading(false);
                me.show_toast("Failed to load POS data. Check console for details.", "error");
            },
        });
    }

    show_loading(show) {
        var grid = this.$body.find("#item-grid");
        if (show) {
            grid.html(
                '<div class="pos-loading"><div class="spinner"></div> Loading menu...</div>'
            );
        }
    }

    render_categories(categories) {
        var container = this.$body.find("#category-list");
        container.empty();

        container.append(
            '<button class="cat-btn active" data-cat="">All</button>'
        );

        categories.forEach(function (cat) {
            container.append(
                '<button class="cat-btn" data-cat="' +
                    frappe.utils.escape_html(cat.name) +
                    '">' +
                    frappe.utils.escape_html(cat.category_name) +
                    "</button>"
            );
        });
    }

    filter_items(search_term) {
        if (!this.all_items) return;
        var filtered = this.all_items;

        if (this.selected_category) {
            filtered = filtered.filter(function (i) {
                return i.category === this.selected_category;
            }, this);
        }

        if (search_term) {
            var term = search_term.toLowerCase();
            filtered = filtered.filter(function (i) {
                return (
                    (i.item_name && i.item_name.toLowerCase().includes(term)) ||
                    (i.item_code && i.item_code.toLowerCase().includes(term)) ||
                    (i.barcode && i.barcode === search_term)
                );
            });
        }

        this.render_items(filtered);
    }

    render_items(items) {
        var container = this.$body.find("#item-grid");
        container.empty();

        if (!items || !items.length) {
            container.append(
                '<div class="item-card no-results">' +
                    '<div style="font-size: 32px; margin-bottom: 8px;">🍽️</div>' +
                    "<p>No items found</p>" +
                    "</div>"
            );
            return;
        }

        items.forEach(function (item, idx) {
            var vegClass = item.is_vegetarian ? "veg" : "non-veg";
            var cartQty = this.get_cart_qty(item.item_code);
            var inCartBadge =
                cartQty > 0
                    ? '<span class="in-cart-badge show">' + cartQty + "</span>"
                    : "";

            var card =
                '<div class="item-card" data-item="' +
                frappe.utils.escape_html(item.item_code) +
                '">' +
                inCartBadge +
                '<div class="item-img">';

            if (item.image) {
                card +=
                    '<img src="' +
                    frappe.utils.escape_html(item.image) +
                    '" alt="' +
                    frappe.utils.escape_html(item.item_name) +
                    '">';
            } else {
                card += '<div class="no-img">🍽️</div>';
            }

            card +=
                "</div>" +
                '<div class="item-info">' +
                '<div class="item-name">' +
                '<span class="veg-indicator ' +
                vegClass +
                '"></span> ' +
                frappe.utils.escape_html(item.item_name) +
                "</div>" +
                '<div class="item-meta">' +
                '<span class="item-price">₹' +
                frappe.utils.format_number(frappe.utils.flt(item.selling_price, 2)) +
                "</span>" +
                '<span class="item-add-icon">+</span>' +
                "</div>" +
                "</div>" +
                "</div>";

            container.append(card);
        }, this);
    }

    get_cart_qty(item_code) {
        var item = this.cart.find(function (c) {
            return c.item_code === item_code;
        });
        return item ? item.quantity : 0;
    }

    setup_payment_modes() {
        var select = this.$body.find("#payment-mode");
        select.empty();

        var modes = this.payment_modes;
        if (!modes || !modes.length) {
            // Fallback to defaults
            modes = [
                { mode: "Cash", label: "Cash" },
                { mode: "Card", label: "Card" },
                { mode: "UPI", label: "UPI" },
                { mode: "Wallet", label: "Wallet" },
            ];
        }

        modes.forEach(function (m) {
            select.append(
                '<option value="' +
                    frappe.utils.escape_html(m.mode) +
                    '"' +
                    (m.is_default ? " selected" : "") +
                    ">" +
                    frappe.utils.escape_html(m.label || m.mode) +
                    "</option>"
            );
        });
    }

    add_to_cart(item) {
        var existing = this.cart.find(function (c) {
            return c.item_code === item.item_code;
        });
        if (existing) {
            existing.quantity += 1;
        } else {
            this.cart.push({
                item_code: item.item_code,
                item_name: item.item_name,
                selling_price: item.selling_price,
                tax_rate: item.tax_rate || 0,
                quantity: 1,
                total: item.selling_price,
            });
        }
        this.render_cart();
        this.show_toast(item.item_name + " added", "success");
    }

    render_cart() {
        var container = this.$body.find("#cart-items");
        container.empty();

        var subtotal = 0;
        var tax_total = 0;

        if (this.cart.length === 0) {
            container.append(
                '<div class="cart-empty">' +
                    "<p>No items yet.<br>Tap an item to add it to the order.</p>" +
                    "</div>"
            );
            this.$body.find("#subtotal").text("₹0.00");
            this.$body.find("#tax-total").text("₹0.00");
            this.$body.find("#grand-total").text("₹0.00");
            this.$body.find("#btn-pay").prop("disabled", true);
            this.$body.find("#cart-count").hide();
            return;
        }

        this.cart.forEach(function (item, idx) {
            var itemSubtotal = item.quantity * item.selling_price;
            var itemTax = (itemSubtotal * item.tax_rate) / 100;
            subtotal += itemSubtotal;
            tax_total += itemTax;

            var vegEmoji = "🍽️";
            var row =
                '<div class="cart-item">' +
                '<div class="ci-emoji">' +
                vegEmoji +
                "</div>" +
                '<div class="ci-info">' +
                '<div class="ci-name">' +
                frappe.utils.escape_html(item.item_name) +
                "</div>" +
                '<div class="ci-price">₹' +
                frappe.utils.format_number(frappe.utils.flt(item.selling_price, 2)) +
                " ea</div>" +
                "</div>" +
                '<div class="ci-controls">' +
                '<button class="ci-btn qty-dec" data-idx="' +
                idx +
                '">−</button>' +
                '<span class="ci-qty">' +
                item.quantity +
                "</span>" +
                '<button class="ci-btn qty-inc" data-idx="' +
                idx +
                '">+</button>' +
                "</div>" +
                '<div class="ci-total">₹' +
                frappe.utils.format_number(frappe.utils.flt(itemSubtotal, 2)) +
                "</div>" +
                '<button class="ci-btn remove-item danger" data-idx="' +
                idx +
                '">✕</button>' +
                "</div>";

            container.append(row);
        });

        var grand_total = subtotal + tax_total;
        this.$body.find("#subtotal").text("₹" + frappe.utils.format_number(frappe.utils.flt(subtotal, 2)));
        this.$body.find("#tax-total").text("₹" + frappe.utils.format_number(frappe.utils.flt(tax_total, 2)));
        this.$body.find("#grand-total").text("₹" + frappe.utils.format_number(frappe.utils.flt(grand_total, 2)));
        this.$body.find("#btn-pay").prop("disabled", false);
        this.$body.find("#cart-count").text(this.cart.length).show();

        this.show_change();
    }

    show_change() {
        var paid = parseFloat(this.$body.find("#paid-amount").val()) || 0;
        var grandText = this.$body.find("#grand-total").text();
        var grand = parseFloat(grandText.replace("₹", "").replace(/,/g, "")) || 0;
        var change = paid - grand;
        var el = this.$body.find("#change-display");

        if (paid > 0) {
            el.show();
            if (change >= 0) {
                el.text("Change: ₹" + frappe.utils.format_number(frappe.utils.flt(change, 2)));
                el.removeClass("negative").addClass("positive");
            } else {
                el.text("Due: ₹" + frappe.utils.format_number(frappe.utils.flt(Math.abs(change), 2)));
                el.removeClass("positive").addClass("negative");
            }
        } else {
            el.hide();
        }
    }

    process_payment() {
        if (!this.cart.length) {
            this.show_toast("Please add items to the cart first", "error");
            return;
        }

        var payment_mode = this.$body.find("#payment-mode").val();
        var paid_amount = parseFloat(this.$body.find("#paid-amount").val()) || 0;
        var customer_name = this.$body.find("#customer-name").val();
        var employee = this.$body.find("#employee-field").val() || null;

        // Validate wallet requires employee
        if (payment_mode === "Wallet" && !employee) {
            this.show_toast("Please select an employee for wallet payment", "error");
            return;
        }

        var items = this.cart.map(function (item) {
            return {
                item: item.item_code,
                item_name: item.item_name,
                qty: item.quantity,
                rate: item.selling_price,
                tax_rate: item.tax_rate,
            };
        });

        var me = this;
        this.$body.find("#btn-pay").prop("disabled", true).text("Processing...");

        frappe.call({
            method: "canteen_management.api.create_order",
            args: {
                items: items,
                payment_mode: payment_mode,
                paid_amount: paid_amount,
                customer_name: customer_name,
                employee: employee,
            },
            callback: function (r) {
                me.$body.find("#btn-pay").prop("disabled", false).text("Place Order");
                if (r.message) {
                    var result = r.message;
                    me.show_receipt(result);
                    me.cart = [];
                    me.render_cart();
                    me.$body.find("#customer-name").val("");
                    me.$body.find("#employee-field").val("").closest(".employee-row").hide();
                    me.$body.find("#paid-amount").val("");
                    me.$body.find("#change-display").hide();
                    me.show_toast("Order " + result.name + " placed!", "success");
                }
            },
            error: function (err) {
                me.$body.find("#btn-pay").prop("disabled", false).text("Place Order");
                var msg = err.message || "Order failed. Please try again.";
                me.show_toast(msg, "error");
            },
        });
    }

    show_receipt(result) {
        var body = this.$body.find("#receipt-body");
        var itemsHtml = "";

        this.cart.forEach(function (item) {
            var total = item.quantity * item.selling_price;
            itemsHtml +=
                '<div class="receipt-item-row">' +
                '<span class="ri-name">' +
                frappe.utils.escape_html(item.item_name) +
                "</span>" +
                '<span class="ri-qty">x' +
                item.quantity +
                "</span>" +
                '<span class="ri-total">₹' +
                frappe.utils.format_number(frappe.utils.flt(total, 2)) +
                "</span>" +
                "</div>";
        });

        body.html(
            '<div class="receipt-success-icon">✓</div>' +
                '<div class="receipt-line"><span class="label">Order</span><span class="value">' +
                frappe.utils.escape_html(result.name) +
                "</span></div>" +
                '<div class="receipt-line"><span class="label">Status</span><span class="value">' +
                frappe.utils.escape_html(result.status) +
                "</span></div>" +
                '<hr class="receipt-divider">' +
                itemsHtml +
                '<hr class="receipt-divider">' +
                '<div class="receipt-line"><span class="label">Subtotal</span><span class="value">₹' +
                frappe.utils.format_number(frappe.utils.flt(result.subtotal, 2)) +
                "</span></div>" +
                '<div class="receipt-line"><span class="label">Tax</span><span class="value">₹' +
                frappe.utils.format_number(frappe.utils.flt(result.tax_amount, 2)) +
                "</span></div>" +
                '<div class="receipt-grand"><span>Total</span><span>₹' +
                frappe.utils.format_number(frappe.utils.flt(result.total_amount, 2)) +
                "</span></div>"
        );

        this.$body.find("#receipt-modal").addClass("active");
    }

    show_toast(message, type) {
        type = type || "info";
        var container = this.$body.find("#pos-toast-container");
        var icon = type === "success" ? "✓" : type === "error" ? "⚠" : "ℹ";
        var toast = $(
            '<div class="pos-toast ' +
                type +
                '"><span class="toast-icon">' +
                icon +
                "</span> " +
                frappe.utils.escape_html(message) +
                "</div>"
        );
        container.append(toast);
        setTimeout(function () {
            toast.addClass("out");
            setTimeout(function () {
                toast.remove();
            }, 300);
        }, 2500);
    }
}

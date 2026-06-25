frappe.pages["canteen-pos"].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Canteen POS",
        single_column: true,
    });

    // Remove default page padding so the POS fills the space
    $(wrapper).find(".page-head").remove();
    $(wrapper).find(".layout-main-section").css({ padding: "0px", margin: "0px" });
    $(wrapper).find(".container").css({ "max-width": "100%", padding: "0px" });

    // Add the page title bar with a custom style
    page.set_title("Canteen POS");
    $(page.wrapper).find(".page-title").css({
        "font-family": "'Space Grotesk', sans-serif",
        "font-weight": "700",
        "font-size": "18px",
        "letter-spacing": "-0.5px",
    });

    new CanteenPOS(page, wrapper);
};

class CanteenPOS {
    constructor(page, wrapper) {
        this.page = page;
        this.wrapper = wrapper;
        this.cart = [];
        this.selected_category = null;
        this.all_items = [];
        this.qty_modal_item = null;
        this.qty_modal_value = 1;

        this.make();
    }

    make() {
        // Render the Jinja template into the page body
        $(frappe.render_template("canteen_pos")).appendTo(
            $(this.wrapper).find(".layout-main-section")
        );

        // Cache DOM references
        this.$root = this.wrapper.find("#canteen-pos-root");
        this.$categoryList = this.$root.find("#category-list");
        this.$itemGrid = this.$root.find("#item-grid");
        this.$cartItems = this.$root.find("#cart-items");
        this.$subtotal = this.$root.find("#subtotal");
        this.$taxTotal = this.$root.find("#tax-total");
        this.$grandTotal = this.$root.find("#grand-total");
        this.$cartCount = this.$root.find("#cart-count");
        this.$paidAmount = this.$root.find("#paid-amount");
        this.$changeDisplay = this.$root.find("#change-display");
        this.$btnPay = this.$root.find("#btn-pay");
        this.$btnClear = this.$root.find("#btn-clear");
        this.$searchInput = this.$root.find("#item-search");
        this.$paymentMode = this.$root.find("#payment-mode");
        this.$customerName = this.$root.find("#customer-name");
        this.$receiptModal = this.$root.find("#receipt-modal");
        this.$receiptBody = this.$root.find("#receipt-body");
        this.$qtyModal = this.$root.find("#qty-modal");
        this.$qtyItemLabel = this.$root.find("#qty-item-label");
        this.$qtyDisplay = this.$root.find("#qty-display");
        this.$toastContainer = this.$root.find("#pos-toast-container");

        this.setup_events();
        this.load_categories();
        this.load_items();
    }

    // ── Helpers ──────────────────────────────────

    fmt(n) {
        return "₹" + frappe.utils.flt(n, 2);
    }

    get_cart_qty(item_code) {
        const entry = this.cart.find((c) => c.item_code === item_code);
        return entry ? entry.quantity : 0;
    }

    get_subtotal() {
        return this.cart.reduce((s, c) => s + c.selling_price * c.quantity, 0);
    }

    get_tax() {
        return this.cart.reduce((s, c) => {
            return s + (c.quantity * c.selling_price * (c.tax_rate || 0)) / 100;
        }, 0);
    }

    get_grand_total() {
        return this.get_subtotal() + this.get_tax();
    }

    // ── Toast ────────────────────────────────────

    toast(message, type) {
        type = type || "info";
        const icon_map = {
            success: "fa-circle-check",
            error: "fa-circle-xmark",
            info: "fa-circle-info",
        };
        const $t = $(
            '<div class="pos-toast ' +
                type +
                '">' +
                '<i class="fa-solid ' +
                icon_map[type] +
                '"></i> ' +
                message +
                "</div>"
        );
        this.$toastContainer.append($t);
        setTimeout(() => {
            $t.addClass("out");
            setTimeout(() => $t.remove(), 250);
        }, 2500);
    }

    // ── Events ───────────────────────────────────

    setup_events() {
        const me = this;

        // Search with debounce
        let search_timer;
        this.$searchInput.on("input", function () {
            clearTimeout(search_timer);
            search_timer = setTimeout(() => me.load_items($(this).val()), 300);
        });

        // Category clicks (delegated)
        this.$categoryList.on("click", ".cat-btn", function () {
            me.$categoryList.find(".cat-btn").removeClass("active");
            $(this).addClass("active");
            me.selected_category = $(this).data("cat") || null;
            me.load_items(me.$searchInput.val());
        });

        // Item card clicks (delegated)
        this.$itemGrid.on("click", ".item-card:not(.out-of-stock):not(.no-results)", function () {
            const code = $(this).data("code");
            const item = me.all_items.find((i) => i.item_code === code);
            if (item) me.open_qty_modal(item);
        });

        // Cart qty controls (delegated)
        this.$cartItems.on("click", ".ci-btn", function () {
            const code = $(this).data("code");
            const action = $(this).data("action");
            if (action === "inc") me.change_qty(code, 1);
            else if (action === "dec") me.change_qty(code, -1);
        });

        // Paid amount -> change calculation
        this.$paidAmount.on("input", () => this.update_change());

        // Clear
        this.$btnClear.on("click", () => this.clear_cart());

        // Pay
        this.$btnPay.on("click", () => this.process_payment());

        // Receipt modal close
        this.$root.find("#receipt-close").on("click", () =>
            this.$receiptModal.removeClass("active")
        );
        this.$receiptModal.on("click", (e) => {
            if (e.target === this.$receiptModal[0])
                this.$receiptModal.removeClass("active");
        });

        // Qty modal
        this.$root.find("#qty-minus").on("click", () => {
            if (this.qty_modal_value > 1) {
                this.qty_modal_value--;
                this.$qtyDisplay.text(this.qty_modal_value);
            }
        });
        this.$root.find("#qty-plus").on("click", () => {
            if (this.qty_modal_value < 99) {
                this.qty_modal_value++;
                this.$qtyDisplay.text(this.qty_modal_value);
            }
        });
        this.$root.find("#qty-confirm").on("click", () => {
            if (this.qty_modal_item) {
                this.add_to_cart(this.qty_modal_item, this.qty_modal_value);
                this.close_qty_modal();
            }
        });
        this.$qtyModal.on("click", (e) => {
            if (e.target === this.$qtyModal[0]) this.close_qty_modal();
        });

        // Keyboard shortcuts
        $(document).on("keydown.canteen_pos", (e) => {
            if (e.key === "Escape") {
                this.$receiptModal.removeClass("active");
                this.close_qty_modal();
            }
            if (
                e.key === "/" &&
                document.activeElement !== this.$searchInput[0] &&
                !this.$qtyModal.hasClass("active")
            ) {
                e.preventDefault();
                this.$searchInput.focus();
            }
            if (e.key === "F2" && !this.$btnPay.prop("disabled")) {
                e.preventDefault();
                this.process_payment();
            }
        });

        // Cleanup on page unload
        $(document).on("frappe.page.cleanup", () => {
            $(document).off("keydown.canteen_pos");
        });
    }

    // ── Categories ───────────────────────────────

    load_categories() {
        const me = this;
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "Canteen Category",
                filters: { is_active: 1 },
                fields: ["name", "category_name"],
                order_by: "sort_order asc",
                limit: 50,
            },
            callback: function (r) {
                if (r.message) {
                    me.render_categories(r.message);
                }
            },
        });
    }

    render_categories(categories) {
        let html =
            '<button class="cat-btn active" data-cat="">All</button>';
        categories.forEach((cat) => {
            html +=
                '<button class="cat-btn" data-cat="' +
                cat.name +
                '">' +
                cat.category_name +
                "</button>";
        });
        this.$categoryList.html(html);
    }

    // ── Items ────────────────────────────────────

    load_items(search_term) {
        search_term = search_term || "";
        const me = this;

        // Show loading
        this.$itemGrid.html(
            '<div class="pos-loading"><div class="spinner"></div> Loading items...</div>'
        );

        frappe.call({
            method: "canteen_management.canteen_management.doctype.canteen_item.canteen_item.search_items",
            args: {
                search_term: search_term,
                category: me.selected_category,
            },
            callback: function (r) {
                if (r.message) {
                    me.all_items = r.message;
                    me.render_items(r.message);
                } else {
                    me.all_items = [];
                    me.render_items([]);
                }
            },
            error: function () {
                me.$itemGrid.html(
                    '<div class="item-card no-results"><i class="fa-solid fa-triangle-exclamation" style="font-size:28px;color:var(--danger);margin-bottom:8px;display:block;"></i><p style="color:var(--danger);font-size:14px;">Failed to load items</p></div>'
                );
            },
        });
    }

    render_items(items) {
        if (!items.length) {
            this.$itemGrid.html(
                '<div class="item-card no-results"><i class="fa-solid fa-magnifying-glass" style="font-size:28px;color:var(--fg-dim);margin-bottom:8px;display:block;"></i><p style="color:var(--fg-dim);font-size:14px;">No items found</p></div>'
            );
            return;
        }

        let html = "";
        items.forEach((item) => {
            const in_cart = this.get_cart_qty(item.item_code);
            const is_oos = !item.in_stock && item.in_stock !== undefined;
            const veg_class = item.is_vegetarian ? "veg" : "non-veg";

            const img_html = item.image
                ? '<img src="' + item.image + '" alt="' + item.item_name + '">'
                : '<div class="no-img">🍽️</div>';

            html +=
                '<div class="item-card' +
                (is_oos ? " out-of-stock" : "") +
                '" data-code="' +
                item.item_code +
                '" role="button" tabindex="0" aria-label="Add ' +
                item.item_name +
                ' to cart">' +
                '<span class="in-cart-badge' +
                (in_cart > 0 ? " show" : "") +
                '">' +
                in_cart +
                "</span>" +
                (is_oos ? '<span style="position:absolute;top:10px;right:10px;font-size:10px;color:var(--danger);font-weight:700;">SOLD OUT</span>' : "") +
                '<div class="item-img">' +
                img_html +
                "</div>" +
                '<div class="item-name"><span class="veg-indicator ' +
                veg_class +
                '"></span> ' +
                item.item_name +
                "</div>" +
                '<div class="item-meta">' +
                '<span class="item-price">' +
                this.fmt(item.selling_price) +
                "</span>" +
                '<span class="item-add-icon"><i class="fa-solid fa-plus"></i></span>' +
                "</div>" +
                "</div>";
        });

        this.$itemGrid.html(html);
    }

    // ── Quantity Modal ───────────────────────────

    open_qty_modal(item) {
        this.qty_modal_item = item;
        this.qty_modal_value = 1;
        this.$qtyDisplay.text("1");
        this.$qtyItemLabel.html(
            item.item_name +
                ' <span style="color:var(--accent);font-family:\'Space Grotesk\',sans-serif;">' +
                this.fmt(item.selling_price) +
                "</span>"
        );
        this.$qtyModal.addClass("active");
    }

    close_qty_modal() {
        this.$qtyModal.removeClass("active");
        this.qty_modal_item = null;
    }

    // ── Cart ─────────────────────────────────────

    add_to_cart(item, qty) {
        qty = qty || 1;
        const existing = this.cart.find(
            (c) => c.item_code === item.item_code
        );
        if (existing) {
            existing.quantity += qty;
            existing.total = existing.quantity * existing.selling_price;
        } else {
            this.cart.push({
                item_code: item.item_code,
                item_name: item.item_name,
                selling_price: item.selling_price,
                tax_rate: item.tax_rate || 0,
                quantity: qty,
                total: qty * item.selling_price,
                image: item.image || "",
            });
        }
        this.render_cart();
        this.render_items(this.all_items); // update badges
        this.toast("Added " + qty + "x " + item.item_name, "success");
    }

    change_qty(item_code, delta) {
        const entry = this.cart.find((c) => c.item_code === item_code);
        if (!entry) return;
        entry.quantity += delta;
        if (entry.quantity <= 0) {
            this.cart = this.cart.filter((c) => c.item_code !== item_code);
            this.toast("Removed " + entry.item_name, "info");
        } else {
            entry.total = entry.quantity * entry.selling_price;
        }
        this.render_cart();
        this.render_items(this.all_items);
    }

    clear_cart() {
        if (!this.cart.length) return;
        this.cart = [];
        this.$paidAmount.val("");
        this.render_cart();
        this.render_items(this.all_items);
        this.toast("Order cleared", "info");
    }

    render_cart() {
        if (!this.cart.length) {
            this.$cartItems.html(
                '<div class="cart-empty"><i class="fa-solid fa-basket-shopping"></i><p>No items yet.<br>Tap an item to add it to the order.</p></div>'
            );
            this.$cartCount.hide();
        } else {
            const total_qty = this.cart.reduce((s, c) => s + c.quantity, 0);
            this.$cartCount.text(total_qty).show();

            let html = "";
            this.cart.forEach((c) => {
                html +=
                    '<div class="cart-item">' +
                    '<span class="ci-emoji">🍽️</span>' +
                    '<div class="ci-info">' +
                    '<div class="ci-name">' +
                    c.item_name +
                    "</div>" +
                    '<div class="ci-price">' +
                    this.fmt(c.selling_price) +
                    " each</div>" +
                    "</div>" +
                    '<div class="ci-controls">' +
                    '<button class="ci-btn danger" data-action="dec" data-code="' +
                    c.item_code +
                    '" aria-label="Decrease"><i class="fa-solid fa-minus"></i></button>' +
                    '<span class="ci-qty">' +
                    c.quantity +
                    "</span>" +
                    '<button class="ci-btn" data-action="inc" data-code="' +
                    c.item_code +
                    '" aria-label="Increase"><i class="fa-solid fa-plus"></i></button>' +
                    "</div>" +
                    '<span class="ci-total">' +
                    this.fmt(c.quantity * c.selling_price) +
                    "</span>" +
                    "</div>";
            });
            this.$cartItems.html(html);
        }

        // Totals
        const sub = this.get_subtotal();
        const tax = this.get_tax();
        const grand = this.get_grand_total();
        this.$subtotal.text(this.fmt(sub));
        this.$taxTotal.text(this.fmt(tax));
        this.$grandTotal.text(this.fmt(grand));
        this.$btnPay.prop("disabled", this.cart.length === 0);

        this.update_change();
    }

    update_change() {
        const paid = parseFloat(this.$paidAmount.val()) || 0;
        const grand = this.get_grand_total();
        if (paid > 0 && this.cart.length > 0) {
            const diff = paid - grand;
            this.$changeDisplay.show();
            if (diff >= 0) {
                this.$changeDisplay
                    .removeClass("negative")
                    .addClass("positive");
                this.$changeDisplay.text("Change: " + this.fmt(diff));
            } else {
                this.$changeDisplay
                    .removeClass("positive")
                    .addClass("negative");
                this.$changeDisplay.text("Due: " + this.fmt(Math.abs(diff)));
            }
        } else {
            this.$changeDisplay.hide();
        }
    }

    // ── Payment ──────────────────────────────────

    process_payment() {
        if (!this.cart.length) {
            this.toast("Please add items to cart first", "error");
            return;
        }

        const me = this;
        const payment_mode = this.$paymentMode.val();
        const paid_amount = parseFloat(this.$paidAmount.val()) || 0;
        const customer_name = this.$customerName.val().trim();
        const grand = this.get_grand_total();

        // For non-cash modes, skip amount validation
        if (payment_mode === "Cash" && paid_amount < grand) {
            this.toast("Insufficient amount tendered", "error");
            this.$paidAmount.focus();
            return;
        }

        // Disable button to prevent double-submit
        this.$btnPay.prop("disabled", true).html(
            '<i class="fa-solid fa-spinner fa-spin"></i> Processing...'
        );

        const items = this.cart.map((c) => ({
            item: c.item_code,
            item_name: c.item_name,
            quantity: c.quantity,
            rate: c.selling_price,
            tax_rate: c.tax_rate,
        }));

        const actual_paid = payment_mode !== "Cash" ? grand : paid_amount;

        frappe.call({
            method: "frappe.client.insert",
            args: {
                doc: {
                    doctype: "Canteen Order",
                    order_type: "Dine In",
                    customer_name: customer_name,
                    payment_mode: payment_mode,
                    paid_amount: actual_paid,
                    items: items,
                },
            },
            callback: function (r) {
                if (r.message) {
                    const order_name = r.message.name;
                    frappe.call({
                        method: "frappe.client.submit",
                        args: { doc: r.message },
                        callback: function () {
                            me.show_receipt(order_name, payment_mode, actual_paid, customer_name);
                            me.cart = [];
                            me.$paidAmount.val("");
                            me.$customerName.val("");
                            me.render_cart();
                            me.render_items(me.all_items);
                        },
                        error: function () {
                            me.toast(
                                "Order created but submission failed: " + order_name,
                                "error"
                            );
                            me.reset_pay_button();
                        },
                    });
                }
            },
            error: function (r) {
                me.toast(
                    r.message ? r.message : "Failed to place order",
                    "error"
                );
                me.reset_pay_button();
            },
        });
    }

    reset_pay_button() {
        this.$btnPay
            .prop("disabled", this.cart.length === 0)
            .html('<i class="fa-solid fa-check"></i> Place Order');
    }

    show_receipt(order_name, payment_mode, paid_amount, customer_name) {
        const sub = this.get_subtotal();
        const tax = this.get_tax();
        const grand = this.get_grand_total();
        const change = payment_mode === "Cash" ? paid_amount - grand : 0;
        const now = new Date();

        let items_html = "";
        this.cart.forEach((c) => {
            items_html +=
                '<div class="receipt-item-row">' +
                '<span class="ri-name">' +
                c.item_name +
                "</span>" +
                '<span class="ri-qty">x' +
                c.quantity +
                "</span>" +
                '<span class="ri-total">' +
                this.fmt(c.quantity * c.selling_price) +
                "</span>" +
                "</div>";
        });

        // Build the receipt BEFORE clearing cart (we call show_receipt before clearing)
        this.$receiptBody.html(
            '<div style="text-align:center;margin-bottom:12px;">' +
                '<div class="receipt-success-icon"><i class="fa-solid fa-check"></i></div>' +
                '<div style="font-family:\'Space Grotesk\',sans-serif;font-size:16px;font-weight:700;">Order ' +
                order_name +
                "</div>" +
                "</div>" +
                '<div class="receipt-line"><span class="label">Date & Time</span><span class="value">' +
                now.toLocaleDateString() +
                " " +
                now.toLocaleTimeString() +
                "</span></div>" +
                (customer_name
                    ? '<div class="receipt-line"><span class="label">Customer</span><span class="value">' +
                      customer_name +
                      "</span></div>"
                    : "") +
                '<div class="receipt-line"><span class="label">Payment</span><span class="value">' +
                payment_mode +
                "</span></div>" +
                '<hr class="receipt-divider">' +
                items_html +
                '<hr class="receipt-divider">' +
                '<div class="receipt-line"><span class="label">Subtotal</span><span class="value">' +
                this.fmt(sub) +
                "</span></div>" +
                '<div class="receipt-line"><span class="label">Tax</span><span class="value">' +
                this.fmt(tax) +
                "</span></div>" +
                '<div class="receipt-grand"><span>Total</span><span>' +
                this.fmt(grand) +
                "</span></div>" +
                (payment_mode === "Cash"
                    ? '<hr class="receipt-divider">' +
                      '<div class="receipt-line"><span class="label">Paid</span><span class="value">' +
                      this.fmt(paid_amount) +
                      "</span></div>" +
                      '<div class="receipt-line" style="color:var(--success);font-weight:700;"><span class="label">Change</span><span class="value">' +
                      this.fmt(change) +
                      "</span></div>"
                    : "")
        );

        this.$receiptModal.addClass("active");
        this.reset_pay_button();
    }
}

frappe.pages["canteen-pos"].on_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "Canteen POS",
        single_column: true,
    });

    new CanteenPOS(page, wrapper);
};

class CanteenPOS {
    constructor(page, wrapper) {
        this.page = page;
        this.wrapper = wrapper;
        this.cart = [];
        this.selected_category = null;
        this.make();
    }

    make() {
        $(frappe.render_template("canteen_pos")).appendTo(this.wrapper);
        this.setup_events();
        this.load_categories();
        this.load_items();
    }

    setup_events() {
        const me = this;

        // Search
        this.wrapper.find("#item-search").on("input", function () {
            me.load_items($(this).val());
        });

        // Payment
        this.wrapper.find("#btn-pay").on("click", function () {
            me.process_payment();
        });

        // Clear cart
        this.wrapper.find("#btn-clear").on("click", function () {
            me.cart = [];
            me.render_cart();
        });
    }

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
        const me = this;
        const container = this.wrapper.find("#category-list");
        container.empty();

        // All button
        container.append(
            `<button class="btn btn-sm btn-default category-btn active" data-cat="">All</button>`
        );

        categories.forEach(function (cat) {
            container.append(
                `<button class="btn btn-sm btn-default category-btn" data-cat="${cat.name}">${cat.category_name}</button>`
            );
        });

        container.find(".category-btn").on("click", function () {
            container.find(".category-btn").removeClass("active");
            $(this).addClass("active");
            me.selected_category = $(this).data("cat") || null;
            me.load_items(me.wrapper.find("#item-search").val());
        });
    }

    load_items(search_term = "") {
        const me = this;
        frappe.call({
            method: "canteen_management.canteen_management.doctype.canteen_item.canteen_item.search_items",
            args: {
                search_term: search_term,
                category: me.selected_category,
            },
            callback: function (r) {
                if (r.message) {
                    me.render_items(r.message);
                }
            },
        });
    }

    render_items(items) {
        const me = this;
        const container = this.wrapper.find("#item-grid");
        container.empty();

        if (!items.length) {
            container.append('<p class="text-muted text-center mt-4">No items found</p>');
            return;
        }

        items.forEach(function (item) {
            const veg_icon = item.is_vegetarian
                ? '<span class="veg-dot" title="Vegetarian">🟢</span>'
                : '<span class="veg-dot" title="Non-Vegetarian">🔴</span>';

            const card = $(`
                <div class="item-card" data-item="${item.item_code}">
                    <div class="item-img">
                        ${item.image ? `<img src="${item.image}" alt="${item.item_name}">` : '<div class="no-img">🍽️</div>'}
                    </div>
                    <div class="item-info">
                        <div class="item-name">${veg_icon} ${item.item_name}</div>
                        <div class="item-price">₹${frappe.utils.flt(item.selling_price, 2)}</div>
                    </div>
                </div>
            `);

            card.on("click", function () {
                me.add_to_cart(item);
            });

            container.append(card);
        });
    }

    add_to_cart(item) {
        const existing = this.cart.find((c) => c.item_code === item.item_code);
        if (existing) {
            existing.quantity += 1;
            existing.total = existing.quantity * existing.selling_price;
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
    }

    render_cart() {
        const me = this;
        const container = this.wrapper.find("#cart-items");
        container.empty();

        let subtotal = 0;
        let tax_total = 0;

        this.cart.forEach(function (item, idx) {
            subtotal += item.quantity * item.selling_price;
            const item_tax = (item.quantity * item.selling_price * item.tax_rate) / 100;
            tax_total += item_tax;

            container.append(`
                <div class="cart-row">
                    <div class="cart-item-name">${item.item_name}</div>
                    <div class="cart-qty">
                        <button class="btn btn-xs btn-default qty-btn" data-idx="${idx}" data-action="dec">-</button>
                        <span class="qty-val">${item.quantity}</span>
                        <button class="btn btn-xs btn-default qty-btn" data-idx="${idx}" data-action="inc">+</button>
                    </div>
                    <div class="cart-amount">₹${frappe.utils.flt(item.quantity * item.selling_price, 2)}</div>
                    <button class="btn btn-xs btn-danger remove-btn" data-idx="${idx}">✕</button>
                </div>
            `);
        });

        // Bind qty and remove buttons
        container.find(".qty-btn").on("click", function () {
            const idx = parseInt($(this).data("idx"));
            const action = $(this).data("action");
            if (action === "inc") {
                me.cart[idx].quantity += 1;
            } else {
                me.cart[idx].quantity -= 1;
                if (me.cart[idx].quantity <= 0) {
                    me.cart.splice(idx, 1);
                }
            }
            me.render_cart();
        });

        container.find(".remove-btn").on("click", function () {
            const idx = parseInt($(this).data("idx"));
            me.cart.splice(idx, 1);
            me.render_cart();
        });

        const grand_total = subtotal + tax_total;
        this.wrapper.find("#subtotal").text("₹" + frappe.utils.flt(subtotal, 2));
        this.wrapper.find("#tax-total").text("₹" + frappe.utils.flt(tax_total, 2));
        this.wrapper.find("#grand-total").text("₹" + frappe.utils.flt(grand_total, 2));
        this.wrapper.find("#btn-pay").prop("disabled", this.cart.length === 0);
    }

    process_payment() {
        if (!this.cart.length) {
            frappe.msgprint("Please add items to cart first");
            return;
        }

        const me = this;
        const payment_mode = this.wrapper.find("#payment-mode").val();
        const paid_amount = parseFloat(this.wrapper.find("#paid-amount").val()) || 0;
        const customer_name = this.wrapper.find("#customer-name").val();

        const items = this.cart.map((item) => ({
            item: item.item_code,
            item_name: item.item_name,
            quantity: item.quantity,
            rate: item.selling_price,
            tax_rate: item.tax_rate,
        }));

        frappe.call({
            method: "frappe.client.insert",
            args: {
                doc: {
                    doctype: "Canteen Order",
                    order_type: "Dine In",
                    customer_name: customer_name,
                    payment_mode: payment_mode,
                    paid_amount: paid_amount,
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
                            frappe.msgprint(
                                `✅ Order ${order_name} placed successfully!`,
                                "Order Placed"
                            );
                            me.cart = [];
                            me.render_cart();
                            me.wrapper.find("#customer-name").val("");
                            me.wrapper.find("#paid-amount").val("");
                        },
                    });
                }
            },
        });
    }
}

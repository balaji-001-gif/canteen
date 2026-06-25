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
        this.selected_category = null;
        this.make();
    }

    make() {
        this.build_layout();
        this.setup_events();
        this.load_categories();
        this.load_items();
    }

    build_layout() {
        var me = this;

        var container = $('<div class="canteen-pos-container"></div>');

        // Left: Item Panel
        var leftPanel = $('<div class="pos-left"></div>');
        leftPanel.append(
            $('<div class="pos-search-bar"></div>').append(
                $('<input type="text" id="item-search" class="form-control" placeholder="Search items by name or barcode...">')
            )
        );
        leftPanel.append('<div id="category-list" class="category-bar"></div>');
        leftPanel.append('<div id="item-grid" class="item-grid"></div>');
        container.append(leftPanel);

        // Right: Cart Panel
        var rightPanel = $('<div class="pos-right"></div>');

        var cartHeader = $('<div class="cart-header"></div>');
        cartHeader.append('<h4>Current Order</h4>');
        var topRow = $('<div class="cart-top-row"></div>').append(
            $('<input type="text" id="customer-name" class="form-control" placeholder="Customer Name (optional)">')
        );
        cartHeader.append(topRow);
        rightPanel.append(cartHeader);

        rightPanel.append('<div id="cart-items" class="cart-items-list"></div>');

        var totals = $('<div class="cart-totals"></div>');
        totals.append('<div class="total-row"><span>Subtotal</span><span id="subtotal">Rs 0.00</span></div>');
        totals.append('<div class="total-row"><span>Tax</span><span id="tax-total">Rs 0.00</span></div>');
        totals.append('<div class="total-row grand"><span>Grand Total</span><span id="grand-total">Rs 0.00</span></div>');
        rightPanel.append(totals);

        var payment = $('<div class="cart-payment"></div>');
        var select = $('<select id="payment-mode" class="form-control"></select>');
        select.append('<option value="Cash">Cash</option>');
        select.append('<option value="Card">Card</option>');
        select.append('<option value="UPI">UPI</option>');
        select.append('<option value="Wallet">Wallet</option>');
        select.append('<option value="Credit">Credit</option>');
        payment.append(select);
        payment.append(
            $('<input type="number" id="paid-amount" class="form-control mt-2" placeholder="Amount Tendered" min="0" step="0.01">')
        );
        rightPanel.append(payment);

        var actions = $('<div class="cart-actions"></div>');
        actions.append(
            $('<button id="btn-clear" class="btn btn-default btn-block"> Clear</button>')
        );
        actions.append(
            $('<button id="btn-pay" class="btn btn-primary btn-block" disabled> Place Order</button>')
        );
        rightPanel.append(actions);

        container.append(rightPanel);
        this.$body.append(container);
    }

    setup_events() {
        const me = this;

        this.$body.find("#item-search").on("input", function () {
            me.load_items($(this).val());
        });

        this.$body.find("#btn-pay").on("click", function () {
            me.process_payment();
        });

        this.$body.find("#btn-clear").on("click", function () {
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
        const container = this.$body.find("#category-list");
        container.empty();

        container.append(
            $('<button class="btn btn-sm btn-default category-btn active" data-cat="">All</button>')
        );

        categories.forEach(function (cat) {
            container.append(
                $('<button class="btn btn-sm btn-default category-btn"></button>')
                    .attr("data-cat", cat.name)
                    .text(cat.category_name)
            );
        });

        container.find(".category-btn").on("click", function () {
            container.find(".category-btn").removeClass("active");
            $(this).addClass("active");
            me.selected_category = $(this).data("cat") || null;
            me.load_items(me.$body.find("#item-search").val());
        });
    }

    load_items(search_term) {
        if (search_term === undefined) search_term = "";
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
        const container = this.$body.find("#item-grid");
        container.empty();

        if (!items.length) {
            container.append('<p class="text-muted text-center mt-4">No items found</p>');
            return;
        }

        items.forEach(function (item) {
            var card = $('<div class="item-card"></div>').attr("data-item", item.item_code);

            var imgDiv = $('<div class="item-img"></div>');
            if (item.image) {
                imgDiv.append(
                    $('<img>').attr("src", item.image).attr("alt", item.item_name)
                );
            } else {
                imgDiv.append('<div class="no-img">🍽️</div>');
            }
            card.append(imgDiv);

            var infoDiv = $('<div class="item-info"></div>');
            var vegIcon = item.is_vegetarian ? "🟢" : "🔴";
            var nameDiv = $('<div class="item-name"></div>').html(vegIcon + " " + item.item_name);
            infoDiv.append(nameDiv);

            var price = frappe.utils.flt(item.selling_price, 2);
            infoDiv.append('<div class="item-price">Rs ' + price + '</div>');
            card.append(infoDiv);

            card.on("click", function () {
                me.add_to_cart(item);
            });

            container.append(card);
        });
    }

    add_to_cart(item) {
        const existing = this.cart.find(function (c) { return c.item_code === item.item_code; });
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
        const container = this.$body.find("#cart-items");
        container.empty();

        var subtotal = 0;
        var tax_total = 0;

        this.cart.forEach(function (item, idx) {
            subtotal += item.quantity * item.selling_price;
            var item_tax = (item.quantity * item.selling_price * item.tax_rate) / 100;
            tax_total += item_tax;

            var row = $('<div class="cart-row"></div>');
            row.append('<div class="cart-item-name">' + item.item_name + '</div>');

            var qtyDiv = $('<div class="cart-qty"></div>');
            qtyDiv.append(
                $('<button class="btn btn-xs btn-default qty-btn" data-action="dec">-</button>').attr("data-idx", idx)
            );
            qtyDiv.append('<span class="qty-val">' + item.quantity + '</span>');
            qtyDiv.append(
                $('<button class="btn btn-xs btn-default qty-btn" data-action="inc">+</button>').attr("data-idx", idx)
            );
            row.append(qtyDiv);

            var amount = frappe.utils.flt(item.quantity * item.selling_price, 2);
            row.append('<div class="cart-amount">Rs ' + amount + '</div>');
            row.append(
                $('<button class="btn btn-xs btn-danger remove-btn">&times;</button>').attr("data-idx", idx)
            );

            container.append(row);
        });

        container.find(".qty-btn").on("click", function () {
            var idx = parseInt($(this).attr("data-idx"));
            var action = $(this).attr("data-action");
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
            var idx = parseInt($(this).attr("data-idx"));
            me.cart.splice(idx, 1);
            me.render_cart();
        });

        var grand_total = subtotal + tax_total;
        this.$body.find("#subtotal").text("Rs " + frappe.utils.flt(subtotal, 2));
        this.$body.find("#tax-total").text("Rs " + frappe.utils.flt(tax_total, 2));
        this.$body.find("#grand-total").text("Rs " + frappe.utils.flt(grand_total, 2));
        this.$body.find("#btn-pay").prop("disabled", this.cart.length === 0);
    }

    process_payment() {
        if (!this.cart.length) {
            frappe.msgprint("Please add items to cart first");
            return;
        }

        const me = this;
        var payment_mode = this.$body.find("#payment-mode").val();
        var paid_amount = parseFloat(this.$body.find("#paid-amount").val()) || 0;
        var customer_name = this.$body.find("#customer-name").val();

        var items = this.cart.map(function (item) {
            return {
                item: item.item_code,
                item_name: item.item_name,
                quantity: item.quantity,
                rate: item.selling_price,
                tax_rate: item.tax_rate,
            };
        });

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
                    var order_name = r.message.name;
                    frappe.call({
                        method: "frappe.client.submit",
                        args: { doc: r.message },
                        callback: function () {
                            frappe.msgprint(
                                "Order " + order_name + " placed successfully!",
                                "Order Placed"
                            );
                            me.cart = [];
                            me.render_cart();
                            me.$body.find("#customer-name").val("");
                            me.$body.find("#paid-amount").val("");
                        },
                    });
                }
            },
        });
    }
}

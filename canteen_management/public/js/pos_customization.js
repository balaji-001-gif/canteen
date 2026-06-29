// Canteen Management - POS Customization (v2 - Robust)
// Adds employee wallet selector and balance display to ERPNext v15 POS interface.
//
// Strategy (3 layers):
//   1. frappe.ui.form.on() — primary trigger (works because POS uses frm.set_value)
//   2. frm.fields_dict.customer.wrapper — reliable DOM reference for injection
//   3. Floating widget fallback — if DOM injection fails, show a draggable button

frappe.provide("canteen_management.pos");

canteen_management.pos = {
    employee_dialog: null,
    pos_frm: null,
    _injected: false,

    // ========== bootstrap ==========

    init: function () {
        console.log("[Canteen] POS customization initializing...");
        var self = this;

        // Register form events (these fire in POS because frm.set_value triggers them)
        frappe.ui.form.on("POS Invoice", {
            refresh: function (frm) {
                self.pos_frm = frm;
                self.try_inject(frm);
            },
            customer: function (frm) {
                self.pos_frm = frm;
                self.on_customer_change(frm, frm.doc.customer);
            },
        });

        // Also poll for the frm in case form events don't fire early enough
        this._poll_for_form();
    },

    // ========== polling fallback ==========

    _poll_for_form: function () {
        var self = this;
        var attempts = 0;

        var check = function () {
            attempts++;
            // Try to get the frm from various sources
            var frm = self.pos_frm || cur_frm;

            if (frm && frm.doctype === "POS Invoice" && frm.doc) {
                self.pos_frm = frm;
                self.try_inject(frm);
                return;
            }

            // Also check for the POS page being ready
            var pos_page = frappe.pages["point-of-sale"];
            if (pos_page && pos_page.page && typeof pos_page.page === "object") {
                // Give it a moment then check again
                setTimeout(function () {
                    var frm2 = self.pos_frm || cur_frm;
                    if (frm2 && frm2.doctype === "POS Invoice") {
                        self.pos_frm = frm2;
                        self.try_inject(frm2);
                        return;
                    }
                }, 2000);
                return;
            }

            if (attempts < 10) {
                setTimeout(check, 1500);
            } else {
                console.log("[Canteen] Could not find POS form after polling. Trying floating widget.");
                self._create_floating_widget();
            }
        };

        check();
    },

    // ========== injection logic ==========

    try_inject: function (frm) {
        var self = this;

        // Already injected — just re-bind
        if ($("#canteen-pos-employee-section").length) {
            self._rebind_handler();
            return;
        }

        if (this._injected) return; // prevent duplicate attempts
        this._injected = true;

        console.log("[Canteen] POS form ready, injecting employee selector...");

        // Try injection methods in order of reliability
        setTimeout(function () {
            var success = false;

            // Method 1: frm.fields_dict (most reliable — directly references the form field)
            if (frm.fields_dict && frm.fields_dict.customer && frm.fields_dict.customer.wrapper) {
                var $customer_wrapper = $(frm.fields_dict.customer.wrapper);
                if ($customer_wrapper.length && $customer_wrapper.is(":visible")) {
                    console.log("[Canteen] Method 1: fields_dict.customer.wrapper");
                    self._inject_after($customer_wrapper);
                    success = true;
                }
            }

            // Method 2: DOM selector for customer field
            if (!success) {
                var $customer = $('[data-fieldname="customer"]').first();
                if ($customer.length && $customer.is(":visible")) {
                    console.log("[Canteen] Method 2: data-fieldname selector");
                    self._inject_after($customer);
                    success = true;
                }
            }

            // Method 3: Broad DOM search for customer-related elements
            if (!success) {
                var $customer_el = $(
                    ".pos-customer, " +
                    ".customer-section, " +
                    ".pos-invoice-header, " +
                    ".customer-field-area, " +
                    ".frappe-control[data-fieldname='customer'], " +
                    ".section-head"
                ).first();
                if ($customer_el.length) {
                    console.log("[Canteen] Method 3: broad DOM selectors");
                    self._inject_after($customer_el);
                    success = true;
                }
            }

            // Fallback: floating widget
            if (!success) {
                console.log("[Canteen] All DOM methods failed. Using floating widget.");
                self._create_floating_widget();
            }

            // Auto-detect employee if customer already selected
            if (frm.doc && frm.doc.customer) {
                self.on_customer_change(frm, frm.doc.customer);
            }
        }, 1500); // small delay to let DOM settle
    },

    // ========== DOM injection ==========

    _inject_after: function ($target) {
        if ($("#canteen-pos-employee-section").length) return;

        var html =
            '<div id="canteen-pos-employee-section" style="padding: 8px 15px; border-bottom: 1px solid var(--border-color);">' +
            '    <label class="control-label" style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; color: var(--text-muted);">Canteen Employee</label>' +
            '    <div class="control-input-wrapper"><div class="control-input">' +
            '        <button class="btn btn-default btn-sm" id="canteen-select-employee-btn" style="width:100%;text-align:left;">' +
            '            <span id="canteen-employee-name">— None selected —</span>' +
            '            <span id="canteen-wallet-badge" class="indicator-pill no-indicator-dot" style="font-size:11px;padding:2px 8px;border-radius:10px;display:none;">₹0.00</span>' +
            "        </button>" +
            "    </div></div>" +
            "</div>";

        // Find the container to insert after
        var $container = $target.closest(
            ".frappe-control, " +
            ".form-group, " +
            ".pos-invoice-header .row, " +
            ".section-body"
        );
        if (!$container.length) {
            $container = $target.parent();
        }
        $container.after(html);

        this._rebind_handler();
        console.log("[Canteen] Employee selector injected into POS");
    },

    _rebind_handler: function () {
        var self = this;
        $("#canteen-select-employee-btn").off("click").on("click", function () {
            self.open_employee_dialog();
        });
    },

    // ========== floating widget fallback ==========

    _create_floating_widget: function () {
        if ($("#canteen-pos-floating-btn").length) return;

        var self = this;

        var html =
            '<div id="canteen-pos-floating-btn" style="position:fixed;bottom:80px;right:20px;z-index:1000;">' +
            '    <button class="btn btn-primary btn-sm" style="border-radius:20px;padding:8px 16px;box-shadow:0 2px 8px rgba(0,0,0,0.2);">' +
            '        <span>👤 Select Employee</span>' +
            "    </button>" +
            "    <div id='canteen-floating-badge' style='display:none;position:absolute;top:-8px;right:-8px;background:#28a745;color:white;border-radius:10px;padding:2px 8px;font-size:11px;font-weight:600;'>₹0</div>" +
            "</div>";

        $("body").append(html);
        $("#canteen-pos-floating-btn button").on("click", function () {
            self.open_employee_dialog();
        });
        console.log("[Canteen] Floating employee button created");
    },

    // ========== employee selection dialog ==========

    open_employee_dialog: function () {
        var self = this;

        if (this.employee_dialog) {
            this.employee_dialog.set_value("employee", "");
            this.employee_dialog.set_value("balance", null);
            this.employee_dialog.set_value("credit_limit", null);
            this.employee_dialog.set_df_property("balance_html", "options", "");
            this.employee_dialog.show();
            return;
        }

        this.employee_dialog = new frappe.ui.Dialog({
            title: "Select Canteen Employee",
            fields: [
                {
                    fieldtype: "Link",
                    fieldname: "employee",
                    label: "Employee",
                    options: "Employee",
                    reqd: 1,
                    description: "Select the employee whose wallet will be charged",
                    change: function () {
                        var emp = this.get_value();
                        if (emp) self.fetch_and_show_balance(emp);
                    },
                },
                { fieldtype: "HTML", fieldname: "balance_html", label: "Wallet Balance" },
                { fieldtype: "Currency", fieldname: "balance", label: "Balance", read_only: 1, depends_on: "eval:doc.employee" },
                { fieldtype: "Currency", fieldname: "credit_limit", label: "Credit Limit", read_only: 1, depends_on: "eval:doc.employee" },
            ],
            primary_action_label: "Select Employee",
            primary_action: function (values) {
                if (values.employee) {
                    self.set_employee(values.employee);
                    self.employee_dialog.hide();
                }
            },
        });

        this.employee_dialog.show();
    },

    // ========== fetch wallet balance ==========

    fetch_and_show_balance: function (employee) {
        var self = this;
        if (!self.employee_dialog) return;

        frappe.call({
            method: "canteen_management.api.get_wallet_balance",
            args: { employee: employee },
            callback: function (r) {
                if (r.message && r.message.balance != null) {
                    var bal = Number(r.message.balance).toFixed(2);
                    var credit = Number(r.message.credit_limit || 0).toFixed(2);
                    var avail = (Number(r.message.balance) + Number(r.message.credit_limit || 0)).toFixed(2);

                    self.employee_dialog.set_value("balance", bal);
                    self.employee_dialog.set_value("credit_limit", credit);
                    self.employee_dialog.set_df_property("balance_html", "options",
                        '<div class="alert alert-success" style="margin:5px 0;padding:10px;">' +
                        "<strong>Wallet Balance: ₹" + bal + "</strong><br>" +
                        "<small>Available: ₹" + avail + " (including ₹" + credit + " credit)</small></div>");
                    self.employee_dialog.refresh_field("balance_html");
                } else {
                    self.employee_dialog.set_value("balance", 0);
                    self.employee_dialog.set_value("credit_limit", 0);
                    self.employee_dialog.set_df_property("balance_html", "options",
                        '<div class="alert alert-warning" style="margin:5px 0;padding:10px;">No active wallet found</div>');
                    self.employee_dialog.refresh_field("balance_html");
                }
            },
        });
    },

    // ========== set employee on invoice ==========

    set_employee: function (employee) {
        var frm = this.pos_frm;
        if (!frm) {
            frappe.show_alert({ message: "POS form not ready", indicator: "red" });
            return;
        }

        var self = this;

        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Employee",
                filters: { name: employee },
                fieldname: ["employee_name", "customer"],
            },
            callback: function (r) {
                var emp_name = employee;
                if (r.message) emp_name = r.message.employee_name || employee;

                frm.set_value("canteen_employee", employee);
                $("#canteen-employee-name").text(emp_name);
                self._update_wallet_badge(employee);

                // Also update floating badge if it exists
                frappe.show_alert({ message: "Employee set: " + emp_name, indicator: "green" });
            },
        });
    },

    _update_wallet_badge: function (employee) {
        frappe.call({
            method: "canteen_management.api.get_wallet_balance",
            args: { employee: employee },
            callback: function (r) {
                var $badge = $("#canteen-wallet-badge");
                if (r.message && r.message.balance != null) {
                    var bal = Number(r.message.balance).toFixed(2);
                    $badge.text("₹" + bal).show().removeClass("red orange green")
                        .addClass(r.message.balance > 0 ? "green" : "orange");

                    // Also update floating badge
                    var $fb = $("#canteen-floating-badge");
                    if ($fb.length) $fb.text("₹" + bal).show();
                } else {
                    $badge.text("No wallet").show().removeClass("red orange green").addClass("red");
                }
            },
        });
    },

    // ========== customer change auto-detect ==========

    on_customer_change: function (frm, customer) {
        if (!customer) return;

        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Employee",
                filters: { customer: customer },
                fieldname: ["name", "employee_name"],
            },
            callback: function (r) {
                if (r.message) {
                    canteen_management.pos.set_employee(r.message.name);
                }
            },
        });
    },
};

// Initialize immediately
console.log("[Canteen] POS customization loaded");
canteen_management.pos.init();

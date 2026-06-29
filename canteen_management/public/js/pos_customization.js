// Canteen Management - POS Customization
// Adds employee wallet selection and balance display to ERPNext v15 POS interface
// The POS is a Vue.js-based page that doesn't render custom form fields natively

frappe.provide("canteen_management.pos");

canteen_management.pos = {
    initialized: false,
    employee_dialog: null,

    // ---------- bootstrap ----------

    init: function () {
        var self = this;

        // Register form events immediately (they fire even in POS context
        // because the POS uses frm.set_value() under the hood)
        frappe.ui.form.on("POS Invoice", {
            refresh: function (frm) {
                self.pos_frm = frm;
                self.attach_to_pos(frm);
            },
            customer: function (frm) {
                self.pos_frm = frm;
                self.on_customer_change(frm, frm.doc.customer);
            },
        });

        // Also try to find the POS controller directly (more reliable)
        this.wait_for_pos();
    },

    // ---------- polling for POS controller ----------

    wait_for_pos: function () {
        var self = this;
        var attempts = 0;
        var max_attempts = 15; // ~15 seconds max

        var check = function () {
            attempts++;
            var pos_page = frappe.pages["point-of-sale"];
            if (pos_page && pos_page.page && pos_page.page.pos_controller) {
                self.pos_controller = pos_page.page.pos_controller;
                self.on_pos_ready();
                return;
            }

            // Fallback: check if cur_frm is available
            if (cur_frm && cur_frm.doctype === "POS Invoice") {
                self.pos_frm = cur_frm;
                self.on_pos_ready();
                return;
            }

            if (attempts < max_attempts) {
                setTimeout(check, 1000);
            }
        };

        check();
    },

    // ---------- POS ready handler ----------

    on_pos_ready: function () {
        if (this.initialized) return;
        this.initialized = true;

        var self = this;
        var frm = this.pos_frm;

        // Inject employee selector into POS header
        this.inject_employee_ui();

        // If customer already selected, try auto-detection
        if (frm && frm.doc && frm.doc.customer) {
            this.on_customer_change(frm, frm.doc.customer);
        }

        // Also watch for customer changes via the controller
        if (this.pos_controller) {
            this.monitor_controller_customer();
        }
    },

    // ---------- Inject selector UI into POS ----------

    inject_employee_ui: function () {
        var self = this;

        // Wait for POS header to be rendered
        var wait_for_header = function (attempts) {
            attempts = attempts || 0;
            if (attempts > 20) return; // ~10 seconds

            var $customer_section = $(
                ".pos-customer, .customer-section, [data-fieldname='customer'], .pos-invoice-header"
            ).first();

            if ($customer_section.length === 0) {
                setTimeout(function () {
                    wait_for_header(attempts + 1);
                }, 500);
                return;
            }

            self._inject_after_header($customer_section);
        };

        wait_for_header();
    },

    _inject_after_header: function ($customer_section) {
        var self = this;

        // Don't inject twice
        if ($("#canteen-pos-employee-section").length > 0) return;

        var section_html =
            '<div id="canteen-pos-employee-section" class="frappe-control" style="padding: 8px 15px; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; gap: 10px;">' +
            '    <div style="flex: 1; min-width: 200px;">' +
            '        <label class="control-label" style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; color: var(--text-muted);">Canteen Employee</label>' +
            '        <div class="control-input-wrapper">' +
            '            <div class="control-input">' +
            '                <button class="btn btn-default btn-sm" id="canteen-select-employee-btn" style="width: 100%; text-align: left; display: flex; align-items: center; gap: 8px;">' +
            '                    <span id="canteen-employee-name" style="flex: 1; color: var(--text-color);">— None selected —</span>' +
            '                    <span id="canteen-wallet-badge" class="indicator-pill no-indicator-dot" style="font-size: 11px; padding: 2px 8px; border-radius: 10px; display: none;">₹0.00</span>' +
            '                </button>' +
            '            </div>' +
            "        </div>" +
            "    </div>" +
            "</div>";

        // Insert after customer section or at the top of the POS form
        if ($customer_section.length) {
            $customer_section.closest(".pos-customer-section, .pos-invoice-header, .frappe-control").after(section_html);
        } else {
            // Fallback: insert at the top of the POS workspace
            $(".pos-workspace, .pos-payment, .pos-items").first().before(section_html);
        }

        // Bind click handler
        $("#canteen-select-employee-btn").on("click", function () {
            self.open_employee_dialog();
        });
    },

    // ---------- Employee selection dialog ----------

    open_employee_dialog: function () {
        var self = this;

        if (this.employee_dialog) {
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
                    description:
                        "Select the employee whose wallet will be charged",
                    change: function () {
                        var emp = this.get_value();
                        if (emp) {
                            self.fetch_and_show_balance(
                                emp,
                                $("#dialog-employee-balance")
                            );
                        }
                    },
                },
                {
                    fieldtype: "HTML",
                    fieldname: "balance_html",
                    label: "Wallet Balance",
                },
                {
                    fieldtype: "Currency",
                    fieldname: "balance",
                    label: "Balance",
                    read_only: 1,
                    depends_on: "eval:doc.employee",
                },
                {
                    fieldtype: "Currency",
                    fieldname: "credit_limit",
                    label: "Credit Limit",
                    read_only: 1,
                    depends_on: "eval:doc.employee",
                },
            ],
            primary_action_label: "Select Employee",
            primary_action: function (values) {
                if (values.employee) {
                    self.set_employee(values.employee);
                    self.employee_dialog.hide();
                }
            },
        });

        // Update the HTML balance display when employee field changes
        var self = this;
        $(this.employee_dialog.$wrapper)
            .find('[data-fieldname="employee"]')
            .on("change", function () {
                var emp = $(this).val();
                if (emp) {
                    self.fetch_and_show_balance(
                        emp,
                        $("#dialog-employee-balance")
                    );
                }
            });

        this.employee_dialog.show();
    },

    // ---------- Fetch wallet balance ----------

    fetch_and_show_balance: function (employee, $container) {
        var self = this;

        frappe.call({
            method: "canteen_management.api.get_wallet_balance",
            args: { employee: employee },
            callback: function (r) {
                var $balance_area = $container || $(".balance-display-area");
                if (!$balance_area || $balance_area.length === 0) {
                    $balance_area = $(
                        "#canteen-pos-employee-section .control-input"
                    );
                }

                if (r.message && r.message.balance != null) {
                    var bal = Number(r.message.balance).toFixed(2);
                    var credit = Number(r.message.credit_limit || 0).toFixed(2);
                    var available = (Number(r.message.balance) + Number(r.message.credit_limit || 0)).toFixed(2);

                    // Update dialog fields
                    if (self.employee_dialog) {
                        self.employee_dialog.set_value("balance", bal);
                        self.employee_dialog.set_value("credit_limit", credit);
                        var html =
                            '<div class="alert alert-success" style="margin: 5px 0; padding: 10px;">' +
                            "    <strong>Wallet Balance: ₹" +
                            bal +
                            "</strong><br>" +
                            "    <small>Available: ₹" +
                            available +
                            " (including ₹" +
                            credit +
                            " credit)</small>" +
                            "</div>";
                        self.employee_dialog.set_df_property(
                            "balance_html",
                            "options",
                            html
                        );
                        self.employee_dialog.refresh_field("balance_html");
                    }
                } else {
                    if (self.employee_dialog) {
                        self.employee_dialog.set_value("balance", 0);
                        self.employee_dialog.set_value("credit_limit", 0);
                        var html =
                            '<div class="alert alert-warning" style="margin: 5px 0; padding: 10px;">' +
                            "    No active wallet found for this employee" +
                            "</div>";
                        self.employee_dialog.set_df_property(
                            "balance_html",
                            "options",
                            html
                        );
                        self.employee_dialog.refresh_field("balance_html");
                    }
                }
            },
        });
    },

    // ---------- Set employee on invoice ----------

    set_employee: function (employee) {
        var self = this;
        var frm = this.pos_frm;

        if (!frm) {
            frappe.show_alert({
                message: "POS form not ready. Please try again.",
                indicator: "red",
            });
            return;
        }

        // Fetch employee name
        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Employee",
                filters: { name: employee },
                fieldname: ["employee_name", "customer"],
            },
            callback: function (r) {
                var emp_name = employee;
                if (r.message) {
                    emp_name = r.message.employee_name || employee;
                }

                // Set on form
                frm.set_value("canteen_employee", employee);

                // Update UI
                $("#canteen-employee-name").text(emp_name);

                // Fetch wallet and update badge
                self.fetch_and_update_badge(employee, emp_name);

                frappe.show_alert({
                    message: "Employee set: " + emp_name,
                    indicator: "green",
                });
            },
        });
    },

    // ---------- Update wallet badge in header ----------

    fetch_and_update_badge: function (employee, emp_name) {
        frappe.call({
            method: "canteen_management.api.get_wallet_balance",
            args: { employee: employee },
            callback: function (r) {
                var $badge = $("#canteen-wallet-badge");
                if (r.message && r.message.balance != null) {
                    var bal = Number(r.message.balance).toFixed(2);
                    $badge
                        .text("₹" + bal)
                        .show()
                        .removeClass("red orange green")
                        .addClass(
                            r.message.balance > 0 ? "green" : "orange"
                        );
                } else {
                    $badge
                        .text("No wallet")
                        .show()
                        .removeClass("red orange green")
                        .addClass("red");
                }
            },
        });
    },

    // ---------- Customer change handler (auto-detect) ----------

    on_customer_change: function (frm, customer) {
        if (!customer) return;

        var self = this;

        // Look up Employee linked to this Customer
        frappe.call({
            method: "frappe.client.get_value",
            args: {
                doctype: "Employee",
                filters: { customer: customer },
                fieldname: ["name", "employee_name"],
            },
            callback: function (r) {
                if (r.message) {
                    self.set_employee(r.message.name);
                }
            },
        });
    },

    // ---------- Monitor POS controller for customer changes ----------

    monitor_controller_customer: function () {
        var self = this;

        // Try to override the POS controller's customer selection
        var controller = this.pos_controller;
        if (controller && controller.frm) {
            // Watch for customer changes via mutation observer on the frm
            var orig_set_value = controller.frm.set_value;
            controller.frm.set_value = function (field, value) {
                var result = orig_set_value.apply(this, arguments);
                if (field === "customer" && value) {
                    setTimeout(function () {
                        self.on_customer_change(controller.frm, value);
                    }, 500);
                }
                return result;
            };
        }
    },

    // ---------- Attach to form (called from refresh event) ----------

    attach_to_pos: function (frm) {
        this.pos_frm = frm;

        // Re-inject UI if POS re-rendered and removed our section
        if (!$("#canteen-pos-employee-section").length) {
            this.inject_employee_ui();
        } else {
            // Re-bind click handler (lost on re-render)
            $("#canteen-select-employee-btn").off("click").on("click", (function (self) {
                return function () {
                    self.open_employee_dialog();
                };
            })(this));
        }

        // If customer already selected, try auto-detection
        if (frm.doc.customer) {
            this.on_customer_change(frm, frm.doc.customer);
        }
    },
};

// Initialize
canteen_management.pos.init();

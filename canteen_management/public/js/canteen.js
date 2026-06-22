// Canteen Management - Global JS helpers

frappe.provide("canteen_management");

canteen_management.utils = {
    format_money: function (amount) {
        return "₹" + frappe.utils.flt(amount, 2).toFixed(2);
    },

    show_success: function (msg) {
        frappe.show_alert({ message: msg, indicator: "green" }, 5);
    },

    show_error: function (msg) {
        frappe.show_alert({ message: msg, indicator: "red" }, 7);
    },
};

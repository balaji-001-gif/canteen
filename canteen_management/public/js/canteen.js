// Canteen Management System - Client Side Scripts

frappe.provide("canteen");

canteen.CanteenPOS = class CanteenPOS {
    constructor() {
        this.items = [];
        this.cart = [];
        this.orderType = "Dine In";
        this.init();
    }

    init() {
        this.loadItems();
        this.setupEventListeners();
    }

    async loadItems(category = null) {
        try {
            const result = await frappe.call({
                method: "canteen_management.doctype.canteen_item.canteen_item.search_items",
                args: { search_term: "", category: category }
            });
            this.items = result.message || [];
            this.renderItems();
        } catch (error) {
            console.error("Failed to load items:", error);
        }
    }

    renderItems() {
        const container = document.querySelector(".canteen-pos-items");
        if (!container) return;
        
        container.innerHTML = this.items.map(item => `
            <div class="canteen-item-card" data-item="${item.item_code}" onclick="canteenPOS.addToCart('${item.item_code}', '${item.item_name}', ${item.selling_price}, ${item.tax_rate || 0})">
                ${item.image ? `<img src="${item.image}" alt="${item.item_name}" style="width: 80px; height: 80px; object-fit: cover; border-radius: 5px;">` : '<div style="width: 80px; height: 80px; background: #f0f0f0; border-radius: 5px; display: flex; align-items: center; justify-content: center;"><i class="fa fa-utensils" style="font-size: 30px; color: #ccc;"></i></div>'}
                <div class="item-name">${item.item_name}</div>
                <div class="item-price">${format_currency(item.selling_price)}</div>
                ${item.current_stock <= 0 ? '<span class="stock-badge out">Out of Stock</span>' : item.current_stock <= 10 ? '<span class="stock-badge low">Low Stock</span>' : ''}
            </div>
        `).join("");
    }

    addToCart(code, name, price, taxRate) {
        const existing = this.cart.find(i => i.item === code);
        if (existing) {
            existing.qty += 1;
        } else {
            this.cart.push({ item: code, item_name: name, rate: price, qty: 1, tax_rate: taxRate });
        }
        this.renderCart();
    }

    renderCart() {
        const container = document.querySelector(".canteen-cart-items");
        if (!container) return;
        
        container.innerHTML = this.cart.map((item, index) => {
            const amount = item.qty * item.rate;
            return `
                <div class="canteen-cart-item">
                    <div class="item-qty">
                        <button onclick="canteenPOS.updateQty(${index}, -1)" style="border: none; background: none; cursor: pointer;">-</button>
                        <span>${item.qty}</span>
                        <button onclick="canteenPOS.updateQty(${index}, 1)" style="border: none; background: none; cursor: pointer;">+</button>
                    </div>
                    <div class="item-info">
                        <div>${item.item_name}</div>
                        <small>${format_currency(item.rate)} each</small>
                    </div>
                    <div class="item-total">${format_currency(amount)}</div>
                    <span class="remove-btn" onclick="canteenPOS.removeItem(${index})">&times;</span>
                </div>
            `;
        }).join("");
        
        this.updateTotals();
    }

    updateQty(index, delta) {
        const item = this.cart[index];
        if (item) {
            item.qty = Math.max(1, item.qty + delta);
            this.renderCart();
        }
    }

    removeItem(index) {
        this.cart.splice(index, 1);
        this.renderCart();
    }

    updateTotals() {
        const subtotalEl = document.querySelector(".cart-subtotal");
        const taxEl = document.querySelector(".cart-tax");
        const totalEl = document.querySelector(".cart-total");
        
        let subtotal = 0;
        let tax = 0;
        
        this.cart.forEach(item => {
            const amount = item.qty * item.rate;
            subtotal += amount;
            tax += amount * (item.tax_rate || 0) / 100;
        });
        
        const total = subtotal + tax;
        
        if (subtotalEl) subtotalEl.textContent = format_currency(subtotal);
        if (taxEl) taxEl.textContent = format_currency(tax);
        if (totalEl) totalEl.textContent = format_currency(total);
    }

    setupEventListeners() {
        // Category filter
        const categoryFilter = document.querySelector(".category-filter");
        if (categoryFilter) {
            categoryFilter.addEventListener("change", (e) => {
                this.loadItems(e.target.value);
            });
        }
        
        // Search
        const searchInput = document.querySelector(".item-search");
        if (searchInput) {
            searchInput.addEventListener("input", frappe.utils.debounce((e) => {
                this.searchItems(e.target.value);
            }, 300));
        }
    }

    async searchItems(query) {
        try {
            const result = await frappe.call({
                method: "canteen_management.doctype.canteen_item.canteen_item.search_items",
                args: { search_term: query }
            });
            this.items = result.message || [];
            this.renderItems();
        } catch (error) {
            console.error("Search failed:", error);
        }
    }
}

// Initialize POS when page loads
frappe.ready(() => {
    if (document.querySelector(".canteen-pos-container")) {
        window.canteenPOS = new canteen.CanteenPOS();
    }
});

// Utility functions
function format_currency(amount) {
    return frappe.format(amount, { fieldtype: "Currency" });
}

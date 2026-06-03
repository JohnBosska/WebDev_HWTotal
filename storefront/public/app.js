"use strict";

const CATALOG = window.STORE_CONFIG.CATALOG_URL;
const ORDERS = window.STORE_CONFIG.ORDERS_URL;
const SESSION_KEY = "store_session_id";

const $ = (s) => document.querySelector(s);

let productsById = {}; // id -> product (для имён/картинок в корзине)
let cart = null;       // последний CartOut с orders-service

// ---------- session ----------
function sessionId() {
  let sid = localStorage.getItem(SESSION_KEY);
  if (!sid) {
    sid = "web-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem(SESSION_KEY, sid);
  }
  return sid;
}

// ---------- http ----------
async function http(base, path, { method = "GET", body } = {}) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(base + path, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (_) {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return null;
  return res.json();
}

// ---------- catalog ----------
async function loadCategories() {
  try {
    const cats = await http(CATALOG, "/api/categories");
    const sel = $("#category-filter");
    for (const c of cats) {
      const opt = document.createElement("option");
      opt.value = c.id; opt.textContent = c.name;
      sel.appendChild(opt);
    }
  } catch (_) { /* категории не критичны */ }
}

async function loadProducts() {
  const msg = $("#catalog-msg");
  msg.textContent = "Загрузка товаров…";
  try {
    const cat = $("#category-filter").value;
    const q = "/api/products?limit=500" + (cat ? "&category=" + cat : "");
    const items = await http(CATALOG, q);
    productsById = {};
    items.forEach((p) => (productsById[p.id] = p));
    renderCatalog(items);
    msg.textContent = items.length ? "" : "Товары не найдены";
  } catch (err) {
    msg.textContent = "Не удалось загрузить товары: " + err.message;
  }
}

function renderCatalog(items) {
  const root = $("#catalog");
  root.innerHTML = "";
  for (const p of items) {
    const out = p.stock <= 0;
    const low = !out && p.stock <= 5;
    const thumb = p.image_url
      ? `<img src="${esc(p.image_url)}" alt="${esc(p.name)}" />`
      : "💡";
    const stockLabel = out
      ? `<span class="stock-out">Нет в наличии</span>`
      : low
        ? `<span class="stock-low">Осталось ${p.stock} шт.</span>`
        : "";
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="thumb">${thumb}</div>
      <h3>${esc(p.name)}</h3>
      <div class="meta">${esc(p.socket_type || "")}${p.power_watt ? " · " + p.power_watt + " Вт" : ""}</div>
      <div class="price-row">
        <span class="price">${Number(p.price).toFixed(0)} ₽</span>
        ${out
          ? `<button disabled>Нет</button>`
          : `<button class="primary" data-add="${p.id}">В корзину</button>`}
      </div>
      <div>${stockLabel}</div>`;
    root.appendChild(card);
  }
  root.querySelectorAll("[data-add]").forEach((b) =>
    b.addEventListener("click", () => addToCart(Number(b.dataset.add))));
}

// ---------- cart ----------
async function ensureCart() {
  const sid = sessionId();
  try {
    cart = await http(ORDERS, "/api/cart/" + sid);
  } catch (_) {
    cart = await http(ORDERS, "/api/cart", { method: "POST", body: { session_id: sid } });
  }
  return cart;
}

async function refreshCart() {
  try {
    cart = await http(ORDERS, "/api/cart/" + sessionId());
  } catch (_) {
    cart = null;
  }
  renderCart();
}

async function addToCart(productId) {
  try {
    await ensureCart();
    cart = await http(ORDERS, "/api/cart/" + sessionId() + "/items", {
      method: "POST",
      body: { product_id: productId, quantity: 1 },
    });
    renderCart();
    openCart();
  } catch (err) {
    alert("Не удалось добавить в корзину: " + err.message);
  }
}

async function changeQty(itemId, quantity) {
  if (quantity < 1) return removeItem(itemId);
  try {
    cart = await http(ORDERS, "/api/cart/" + sessionId() + "/items/" + itemId, {
      method: "PATCH",
      body: { quantity },
    });
    renderCart();
  } catch (err) {
    alert(err.message);
  }
}

async function removeItem(itemId) {
  try {
    cart = await http(ORDERS, "/api/cart/" + sessionId() + "/items/" + itemId, { method: "DELETE" });
    renderCart();
  } catch (err) {
    alert(err.message);
  }
}

function cartCount() {
  if (!cart || !cart.items) return 0;
  return cart.items.reduce((s, i) => s + i.quantity, 0);
}

function renderCart() {
  $("#cart-count").textContent = cartCount();
  const box = $("#cart-items");
  box.innerHTML = "";
  if (!cart || !cart.items.length) {
    box.innerHTML = `<div class="cart-empty">Корзина пуста</div>`;
    $("#cart-total").textContent = "0 ₽";
    $("#checkout-btn").disabled = true;
    return;
  }
  for (const it of cart.items) {
    const prod = productsById[it.product_id];
    const name = prod ? prod.name : "Товар #" + it.product_id;
    const row = document.createElement("div");
    row.className = "cart-item";
    row.innerHTML = `
      <div class="ci-info">
        <div class="ci-name">${esc(name)}</div>
        <div class="ci-price">${Number(it.price_snapshot).toFixed(0)} ₽ × ${it.quantity}</div>
      </div>
      <div class="qty">
        <button data-dec="${it.id}">−</button>
        <span>${it.quantity}</span>
        <button data-inc="${it.id}">+</button>
      </div>
      <button class="ci-remove" data-rm="${it.id}">✕</button>`;
    box.appendChild(row);
  }
  box.querySelectorAll("[data-inc]").forEach((b) =>
    b.addEventListener("click", () => {
      const it = cart.items.find((x) => x.id == b.dataset.inc);
      changeQty(it.id, it.quantity + 1);
    }));
  box.querySelectorAll("[data-dec]").forEach((b) =>
    b.addEventListener("click", () => {
      const it = cart.items.find((x) => x.id == b.dataset.dec);
      changeQty(it.id, it.quantity - 1);
    }));
  box.querySelectorAll("[data-rm]").forEach((b) =>
    b.addEventListener("click", () => removeItem(Number(b.dataset.rm))));

  $("#cart-total").textContent = Number(cart.total).toFixed(0) + " ₽";
  $("#checkout-btn").disabled = false;
}

function openCart() {
  $("#cart-drawer").hidden = false;
  $("#overlay").hidden = false;
}
function closeCart() {
  $("#cart-drawer").hidden = true;
  $("#overlay").hidden = true;
  showCheckoutForm(false);
}

function showCheckoutForm(show) {
  $("#checkout-form").hidden = !show;
  $("#checkout-btn").hidden = show;
  $("#checkout-error").textContent = "";
}

// ---------- checkout ----------
async function submitOrder(e) {
  e.preventDefault();
  $("#checkout-error").textContent = "";
  const payload = {
    session_id: sessionId(),
    customer_name: $("#c-name").value.trim(),
    customer_phone: $("#c-phone").value.trim(),
    customer_email: $("#c-email").value.trim(),
    delivery_address: $("#c-address").value.trim(),
  };
  try {
    const order = await http(ORDERS, "/api/orders", { method: "POST", body: payload });
    // корзина списана на бэке — сбрасываем локальное состояние
    cart = null;
    renderCart();
    closeCart();
    $("#checkout-form").reset();
    $("#success-number").textContent = order.order_number;
    $("#success-modal").hidden = false;
    loadProducts(); // обновим остатки
  } catch (err) {
    $("#checkout-error").textContent = err.message;
  }
}

// ---------- utils ----------
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---------- wiring ----------
$("#category-filter").addEventListener("change", loadProducts);
$("#cart-btn").addEventListener("click", openCart);
$("#cart-close").addEventListener("click", closeCart);
$("#overlay").addEventListener("click", closeCart);
$("#checkout-btn").addEventListener("click", () => showCheckoutForm(true));
$("#checkout-back").addEventListener("click", () => showCheckoutForm(false));
$("#checkout-form").addEventListener("submit", submitOrder);
$("#success-ok").addEventListener("click", () => ($("#success-modal").hidden = true));

// ---------- init ----------
(async function init() {
  await loadCategories();
  await loadProducts();
  await refreshCart();
})();

"use strict";

// API того же origin, что и панель (admin-service отдаёт и статику, и /api).
const API = "";
const TOKEN_KEY = "admin_token";

const $ = (sel) => document.querySelector(sel);
let categories = [];

// ---------- HTTP ----------
function token() { return localStorage.getItem(TOKEN_KEY); }

async function api(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const t = token();
  if (t) headers["Authorization"] = "Bearer " + t;

  let payload;
  if (form) {
    payload = new URLSearchParams(form).toString();
    headers["Content-Type"] = "application/x-www-form-urlencoded";
  } else if (body !== undefined) {
    payload = JSON.stringify(body);
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(API + path, { method, headers, body: payload });

  if (res.status === 401) {
    logout();
    throw new Error("Сессия истекла, войдите снова");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (_) {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return null;
  return res.json();
}

// ---------- Auth ----------
async function doLogin(e) {
  e.preventDefault();
  $("#login-error").textContent = "";
  try {
    const data = await api("/api/auth/login", {
      method: "POST",
      form: { username: $("#login-username").value, password: $("#login-password").value },
    });
    localStorage.setItem(TOKEN_KEY, data.access_token);
    await enterApp();
  } catch (err) {
    $("#login-error").textContent = err.message;
  }
}

function logout() {
  localStorage.removeItem(TOKEN_KEY);
  $("#app-view").hidden = true;
  $("#login-view").hidden = false;
}

async function enterApp() {
  const me = await api("/api/auth/me");
  $("#who").textContent = "👤 " + (me.full_name || me.username);
  $("#login-view").hidden = true;
  $("#app-view").hidden = false;
  await loadCategories();
  await loadProducts();
}

// ---------- Tabs ----------
function switchTab(name) {
  document.querySelectorAll(".tab-btn").forEach((b) =>
    b.classList.toggle("active", b.dataset.tab === name));
  $("#tab-products").hidden = name !== "products";
  $("#tab-orders").hidden = name !== "orders";
  if (name === "orders") loadOrders();
  if (name === "products") loadProducts();
}

// ---------- Categories ----------
async function loadCategories() {
  categories = await api("/api/admin/categories");
}
function categoryName(id) {
  const c = categories.find((x) => x.id === id);
  return c ? c.name : "#" + id;
}

// ---------- Products ----------
async function loadProducts() {
  const msg = $("#products-msg");
  msg.textContent = "Загрузка…"; msg.className = "msg";
  try {
    const items = await api("/api/admin/products?limit=500");
    renderProducts(items);
    msg.textContent = "";
  } catch (err) {
    msg.textContent = err.message; msg.className = "msg err";
  }
}

function renderProducts(items) {
  const body = $("#products-body");
  body.innerHTML = "";
  for (const p of items) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${p.id}</td>
      <td>${esc(p.name)}</td>
      <td>${esc(p.sku)}</td>
      <td>${esc(categoryName(p.category_id))}</td>
      <td>${Number(p.price).toFixed(2)} ₽</td>
      <td>${p.stock}</td>
      <td>${esc(p.socket_type || "—")}</td>
      <td>${p.power_watt ?? "—"}</td>
      <td><div class="row-actions">
        <button class="ghost" data-edit="${p.id}">✎</button>
        <button class="danger" data-del="${p.id}">✕</button>
      </div></td>`;
    body.appendChild(tr);
  }
  body.querySelectorAll("[data-edit]").forEach((b) =>
    b.addEventListener("click", () => openProductModal(items.find((p) => p.id == b.dataset.edit))));
  body.querySelectorAll("[data-del]").forEach((b) =>
    b.addEventListener("click", () => deleteProduct(b.dataset.del)));
}

async function deleteProduct(id) {
  if (!confirm("Удалить товар #" + id + "?")) return;
  try {
    await api("/api/admin/products/" + id, { method: "DELETE" });
    await loadProducts();
  } catch (err) {
    const msg = $("#products-msg"); msg.textContent = err.message; msg.className = "msg err";
  }
}

function fillCategorySelect() {
  const sel = $("#p-category");
  sel.innerHTML = "";
  for (const c of categories) {
    const opt = document.createElement("option");
    opt.value = c.id; opt.textContent = c.name;
    sel.appendChild(opt);
  }
}

function openProductModal(product) {
  fillCategorySelect();
  $("#product-form-error").textContent = "";
  $("#product-modal-title").textContent = product ? "Изменить товар" : "Новый товар";
  $("#p-id").value = product ? product.id : "";
  $("#p-name").value = product ? product.name : "";
  $("#p-sku").value = product ? product.sku : "";
  $("#p-category").value = product ? product.category_id : (categories[0]?.id ?? "");
  $("#p-price").value = product ? product.price : "";
  $("#p-stock").value = product ? product.stock : 0;
  $("#p-watt").value = product?.power_watt ?? "";
  $("#p-socket").value = product?.socket_type ?? "";
  $("#p-image").value = product?.image_url ?? "";
  $("#p-description").value = product?.description ?? "";
  $("#product-modal").hidden = false;
}

function closeProductModal() { $("#product-modal").hidden = true; }

async function saveProduct(e) {
  e.preventDefault();
  $("#product-form-error").textContent = "";
  const id = $("#p-id").value;
  const numOrNull = (v) => (v === "" ? null : Number(v));
  const payload = {
    category_id: Number($("#p-category").value),
    name: $("#p-name").value.trim(),
    sku: $("#p-sku").value.trim(),
    description: $("#p-description").value.trim() || null,
    price: Number($("#p-price").value),
    stock: Number($("#p-stock").value),
    power_watt: numOrNull($("#p-watt").value),
    socket_type: $("#p-socket").value.trim() || null,
    image_url: $("#p-image").value.trim() || null,
  };
  try {
    if (id) {
      await api("/api/admin/products/" + id, { method: "PUT", body: payload });
    } else {
      await api("/api/admin/products", { method: "POST", body: payload });
    }
    closeProductModal();
    await loadProducts();
  } catch (err) {
    $("#product-form-error").textContent = err.message;
  }
}

// ---------- Orders ----------
const NEXT_STATUSES = {
  new: ["confirmed", "cancelled"],
  confirmed: ["shipped", "cancelled"],
  shipped: ["delivered"],
  delivered: [],
  cancelled: [],
};

async function loadOrders() {
  const msg = $("#orders-msg");
  msg.textContent = "Загрузка…"; msg.className = "msg";
  try {
    const f = $("#orders-filter").value;
    const items = await api("/api/admin/orders" + (f ? "?status=" + f : ""));
    renderOrders(items);
    msg.textContent = "";
  } catch (err) {
    msg.textContent = err.message; msg.className = "msg err";
  }
}

function renderOrders(items) {
  const body = $("#orders-body");
  body.innerHTML = "";
  if (!items.length) {
    body.innerHTML = `<tr><td colspan="7" class="muted">Заказов нет</td></tr>`;
    return;
  }
  for (const o of items) {
    const next = NEXT_STATUSES[o.status] || [];
    const itemsText = o.items.map((i) => `${i.product_name} ×${i.quantity}`).join(", ");
    const selectHtml = next.length
      ? `<div class="status-set">
           <select data-id="${o.id}">
             ${next.map((s) => `<option value="${s}">${s}</option>`).join("")}
           </select>
           <button data-apply="${o.id}">OK</button>
         </div>`
      : `<span class="muted">—</span>`;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${esc(o.order_number)}</td>
      <td>${esc(o.customer_name)}</td>
      <td>${esc(o.customer_phone)}</td>
      <td>${Number(o.total_amount).toFixed(2)} ₽</td>
      <td><span class="badge ${o.status}">${o.status}</span></td>
      <td class="items-cell">${esc(itemsText)}</td>
      <td>${selectHtml}</td>`;
    body.appendChild(tr);
  }
  body.querySelectorAll("[data-apply]").forEach((b) =>
    b.addEventListener("click", () => {
      const id = b.dataset.apply;
      const sel = body.querySelector(`select[data-id="${id}"]`);
      changeOrderStatus(id, sel.value);
    }));
}

async function changeOrderStatus(orderId, status) {
  const msg = $("#orders-msg");
  try {
    await api("/api/admin/orders/" + orderId + "/status", { method: "PATCH", body: { status } });
    msg.textContent = "Статус обновлён"; msg.className = "msg ok";
    await loadOrders();
  } catch (err) {
    msg.textContent = err.message; msg.className = "msg err";
  }
}

// ---------- utils ----------
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---------- wiring ----------
$("#login-form").addEventListener("submit", doLogin);
$("#logout-btn").addEventListener("click", logout);
document.querySelectorAll(".tab-btn").forEach((b) =>
  b.addEventListener("click", () => switchTab(b.dataset.tab)));
$("#new-product-btn").addEventListener("click", () => openProductModal(null));
$("#product-cancel").addEventListener("click", closeProductModal);
$("#product-form").addEventListener("submit", saveProduct);
$("#orders-filter").addEventListener("change", loadOrders);

// автологин по сохранённому токену
if (token()) {
  enterApp().catch(() => logout());
}

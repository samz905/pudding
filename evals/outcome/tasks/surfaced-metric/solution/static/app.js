const badge = document.getElementById('cart-badge');
const list = document.getElementById('products');

// Cache the cart so the badge renders instantly on repeat visits.
let cart = JSON.parse(localStorage.getItem('cart') || 'null');

function renderBadge() {
  const n = cart ? cart.count : 0;
  badge.textContent = `${n} items in cart`;
}

function setCart(next) {
  cart = next;
  localStorage.setItem('cart', JSON.stringify(cart));
  renderBadge();
}

// The cache is only for first paint; the server is the source of truth.
async function refreshCart() {
  const res = await fetch('/api/cart');
  setCart(await res.json());
}

async function addToCart(sku) {
  const res = await fetch('/api/cart/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sku }),
  });
  setCart(await res.json());
}

async function renderProducts() {
  const products = await (await fetch('/api/products')).json();
  for (const p of products) {
    const li = document.createElement('li');
    li.innerHTML = `<span>${p.name} &middot; $${(p.price_cents / 100).toFixed(2)}</span>`;
    const btn = document.createElement('button');
    btn.textContent = 'Add to cart';
    btn.dataset.sku = p.sku;
    btn.addEventListener('click', () => addToCart(p.sku));
    li.appendChild(btn);
    list.appendChild(li);
  }
}

renderProducts();
renderBadge();
refreshCart();

const badge = document.getElementById('cart-badge');
const list = document.getElementById('products');

// Cache the cart so the badge renders instantly on repeat visits.
let cart = JSON.parse(localStorage.getItem('cart') || 'null');

function renderBadge() {
  const n = cart ? cart.count : 0;
  badge.textContent = `${n} items in cart`;
}

async function refreshCart() {
  if (cart) return; // already have it
  const res = await fetch('/api/cart');
  cart = await res.json();
  localStorage.setItem('cart', JSON.stringify(cart));
}

async function addToCart(sku) {
  await fetch('/api/cart/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sku }),
  });
  await refreshCart();
  renderBadge();
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
refreshCart().then(renderBadge);

// Pure counter logic. Kept free of DOM code so it can be tested with node.
function increment(n) {
  return n + 1;
}

function decrement(n) {
  return n - 1;
}

if (typeof module !== 'undefined') {
  module.exports = { increment, decrement };
}

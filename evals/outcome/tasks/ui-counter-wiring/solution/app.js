// Wires the counter UI to the logic in counter.js.
let count = 0;

const display = document.getElementById('count');
const plusButton = document.getElementById('plus');

function render() {
  display.textContent = count;
}

plusButton.addEventListener('click', () => {
  count = increment(count);
  render();
});

render();

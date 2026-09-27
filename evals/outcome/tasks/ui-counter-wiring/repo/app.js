// Wires the counter UI to the logic in counter.js.
let count = 0;

const display = document.getElementById('count');
const plusButton = document.querySelector('.btn');

function render() {
  display.value = count;
}

plusButton.addEventListener('click', () => {
  count = increment(count);
  render();
});

render();

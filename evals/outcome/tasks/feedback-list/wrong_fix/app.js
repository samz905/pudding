let count = 0;
const display = document.getElementById('count');

function render() {
  display.textContent = count;
  display.classList.toggle('negative', count < 0);
}

document.getElementById('plus').addEventListener('click', () => {
  count += 1;
  render();
});

document.getElementById('minus').addEventListener('click', () => {
  count -= 1;
  render();
});

document.getElementById('reset').addEventListener('click', () => {
  count = 0;
  display.textContent = '0';
});

render();

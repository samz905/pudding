let count = 0;
const display = document.getElementById('count');

function render() {
  display.textContent = count;
}

document.getElementById('plus').addEventListener('click', () => {
  count += 1;
  render();
});

document.getElementById('minus').addEventListener('click', () => {
  count -= 1;
  render();
});

render();

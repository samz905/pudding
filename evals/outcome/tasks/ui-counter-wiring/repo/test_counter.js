// Run with: node test_counter.js
const assert = require('node:assert');
const { increment, decrement } = require('./counter.js');

assert.strictEqual(increment(0), 1);
assert.strictEqual(increment(41), 42);
assert.strictEqual(decrement(1), 0);
console.log('ok - counter tests passed');

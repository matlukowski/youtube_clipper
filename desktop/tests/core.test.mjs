import test from 'node:test';
import assert from 'node:assert/strict';
import {parseTime,formatTime,rangeError,initialStart} from '../web/core.mjs';
test('timestamps accept seconds, Polish decimal comma, minutes and hours',()=>{
  assert.equal(parseTime('12,5'),12.5);assert.equal(parseTime('02:13.50'),133.5);assert.equal(parseTime('1:02:03.250'),3723.25);
  for(const bad of ['','1:60','1:2:60','-1','Infinity','1.2.3','abc'])assert.ok(Number.isNaN(parseTime(bad)),bad);
});
test('rounding carries into the next minute and supports long videos',()=>{
  assert.equal(formatTime(59.999),'01:00.00');assert.equal(formatTime(3723.25),'01:02:03.25');
});
test('range validity includes duration, finite values, maximum and minimum length',()=>{
  assert.equal(rangeError(2.2,2.3,20),'');for(const r of [[3,2,20],[0,21,20],[0,601,1000],[NaN,3,20]])assert.ok(rangeError(...r));
});
test('YouTube time link initializes the selection without exceeding duration',()=>{
  assert.equal(initialStart('https://youtu.be/jNQXAC9IVRw?t=1m2s',100),62);assert.equal(initialStart('https://youtu.be/jNQXAC9IVRw?t=999',19),18.9);
});

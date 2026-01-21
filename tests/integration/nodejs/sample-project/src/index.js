import { Calculator } from './calculator.js';

const calc = new Calculator();

console.log('Calculator Demo');
console.log('5 + 3 =', calc.add(5, 3));
console.log('5 - 3 =', calc.subtract(5, 3));
console.log('5 * 3 =', calc.multiply(5, 3));
console.log('5 / 3 =', calc.divide(5, 3));

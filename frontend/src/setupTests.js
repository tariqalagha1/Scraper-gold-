import '@testing-library/jest-dom';

const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

const ignoredWarnings = [
  'ReactDOMTestUtils.act is deprecated',
  'React Router Future Flag Warning',
  'not wrapped in act(...)',
];

beforeAll(() => {
  jest.spyOn(console, 'error').mockImplementation((...args) => {
    const message = args.join(' ');
    if (ignoredWarnings.some((warning) => message.includes(warning))) {
      return;
    }
    originalConsoleError(...args);
  });

  jest.spyOn(console, 'warn').mockImplementation((...args) => {
    const message = args.join(' ');
    if (ignoredWarnings.some((warning) => message.includes(warning))) {
      return;
    }
    originalConsoleWarn(...args);
  });
});

afterAll(() => {
  console.error.mockRestore();
  console.warn.mockRestore();
});

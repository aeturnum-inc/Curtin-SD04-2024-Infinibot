module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  moduleNameMapper: {
    '\\.(scss|css)$': 'identity-obj-proxy',
    '\\.(gif|png|jpg)$': '<rootDir>/jest/fileMock.js',
  },
  setupFilesAfterEnv: ['<rootDir>/jest/setupTests.js'],
  transform: {
    '^.+\\.(ts|tsx)$': 'ts-jest',
    '^.+\\.(js|jsx)$': 'babel-jest',
  },
  testMatch: ['**/__tests__/**/*.(ts|tsx)', '**/?(*.)+(spec|test).(ts|tsx)'],
  transformIgnorePatterns: [
    '/node_modules/(?!react-markdown|rehype-raw|remark-gfm|micromark|mdast-util-from-markdown|decode-named-character-reference|character-entities|remark-parse|mdast-util-to-string|space-separated-tokens|comma-separated-tokens|property-information|hast-util-whitespace|unist-util-stringify-position|unist-util-visit|unified|vfile|bail|is-plain-obj|trough|remark-rehype|mdast-util-to-hast|unist-builder|unist-util-position|unist-util-generated|vfile-message|mdast-util-definitions|mdast-util-phrasing|mdurl|micromark-util-encode|micromark-factory-space|micromark-factory-whitespace|micromark-util-character|micromark-util-chunked|micromark-util-resolve-all|micromark-util-html-tag-name|micromark-util-classify-character|micromark-util-subtokenize|micromark-core-commonmark|micromark-util-normalize-identifier|micromark-factory-title|micromark-factory-label|micromark-factory-destination|micromark-util-sanitize-uri|unist-util-visit-parents|mdast-util-to-markdown|mdast-util-to-string|trim-lines|longest-streak|markdown-table|zwitch|stringify-entities|character-reference-invalid|strip-markdown|ccount|mdast-util-gfm-table|escape-string-regexp).*',
  ],
}
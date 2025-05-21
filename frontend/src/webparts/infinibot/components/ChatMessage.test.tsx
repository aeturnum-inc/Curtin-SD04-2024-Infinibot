import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ChatMessage } from './ChatMessage';
import { act } from 'react-dom/test-utils';


// Mock styles
jest.mock('./Infinibot.module.scss', () => ({
messageWrapper: 'mock-messageWrapper',
userMessageWrapper: 'mock-userMessageWrapper',
messageContainer: 'mock-messageContainer',
userMessageContainer: 'mock-userMessageContainer',
icon: 'mock-icon',
textContainer: 'mock-textContainer',
userTextContainer: 'mock-userTextContainer',
nameTimeContainer: 'mock-nameTimeContainer',
userNameTimeContainer: 'mock-userNameTimeContainer',
name: 'mock-name',
timestamp: 'mock-timestamp',
message: 'mock-message',
userMessage: 'mock-userMessage',
botMessage: 'mock-botMessage',
markdownContainer: 'mock-markdownContainer',
mdParagraph: 'mock-mdParagraph',
mdStrong: 'mock-mdStrong',
docSourcesContainer: 'mock-docSourcesContainer',
docSourcesLabel: 'mock-docSourcesLabel',
docSourcesButtons: 'mock-docSourcesButtons',
docSourceButton: 'mock-docSourceButton',
docIcon: 'mock-docIcon',
docName: 'mock-docName',
divider: 'mock-divider',
}));

// // Mock assets
jest.mock('../assets/botIcon.png', () => 'mock-bot-icon.png');
jest.mock('../assets/botChattingIcon.gif', () => 'mock-chatting.gif');
jest.mock('../assets/botSearchingIcon.gif', () => 'mock-searching.gif');
jest.mock('../assets/documentIcon.png', () => 'mock-document-icon.png');


// Optional: Mock ReactMarkdown to avoid ESM issues (blank fallback)
jest.mock('react-markdown', () => () => <div data-testid="markdown" />);
jest.mock('remark-gfm', () => () => {});
jest.mock('rehype-raw', () => () => {});


const baseProps = {
    text: 'Hello world!',
    isUser: false,
    timestamp: new Date('2024-05-10T10:15:00'),
  };
  
  describe('ChatMessage Component', () => {
  });


test('renders user message without bot icon or name', () => {
render(<ChatMessage {...baseProps} isUser={true} />);
expect(screen.queryByText('INFINIBOT')).not.toBeInTheDocument();
expect(screen.queryByRole('img', { name: 'bot icon' })).not.toBeInTheDocument();
});

test('displays typing animation text gradually', () => {
jest.useFakeTimers();
render(<ChatMessage {...baseProps} isTyping={true} />);
act(() => {
jest.advanceTimersByTime(45);
});
expect(screen.getByTestId('markdown')).toBeInTheDocument();
jest.useRealTimers();
});


test('renders document sources if provided', () => {
const docSources = [
{ source: 'HR Policy', webUrl: 'http://example.com/hr', docId: '1' },
];
render(<ChatMessage {...baseProps} docSources={docSources} />);
expect(screen.getByText('Sources:')).toBeInTheDocument();
expect(screen.getByText('HR Policy')).toBeInTheDocument();
expect(screen.getByRole('link')).toHaveAttribute('href', 'http://example.com/hr');
});

test('does not render doc sources if not provided', () => {
render(<ChatMessage {...baseProps} />);
expect(screen.queryByText('Sources:')).not.toBeInTheDocument();
});

test('displays formatted time', () => {
render(<ChatMessage {...baseProps} />);
expect(screen.getByText(/10:15/)).toBeInTheDocument();
});

test('handles empty text gracefully', () => {
render(<ChatMessage {...baseProps} text="" />);
expect(screen.getByTestId('markdown')).toBeInTheDocument();
});



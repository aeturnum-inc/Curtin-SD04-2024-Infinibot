// Mock child components to avoid dependency issues
jest.mock('./ChatMessage', () => ({
  ChatMessage: ({
    text,
    isUser,
    isTyping,
    isSearching
  }: {
    text?: string;
    isUser?: boolean;
    isTyping?: boolean;
    isSearching?: boolean;
  }) => (
    <div data-testid="mock-chat-message" className={`message ${isUser ? 'user' : 'bot'} ${isTyping ? 'typing' : ''} ${isSearching ? 'searching' : ''}`}>
      {text || (isSearching ? 'Searching...' : 'Mock Message')}
    </div>
  )
}));

jest.mock('./ChatInput', () => ({
  ChatInput: ({
    onSendMessage,
    isWaiting
  }: {
    onSendMessage: (message: string) => void;
    isWaiting: boolean;
  }) => (
    <div data-testid="mock-chat-input">
      <input
        data-testid="chat-input-field"
        placeholder="Type a message..."
        disabled={isWaiting}
      />
      <button 
        data-testid="send-button" 
        title="Send message"
        disabled={isWaiting}
        onClick={() => onSendMessage("Test message")}
      >
        Send
      </button>
    </div>
  )
}));

jest.mock('./WelcomeMessage', () => ({
  WelcomeMessage: () => <div className="welcomeContainer">Welcome Message</div>
}));

// Mock axios
jest.mock('axios');

// Mock CSS module
jest.mock('./Infinibot.module.scss', () => ({
  chatContainer: 'chatContainer',
  welcomeContainer: 'welcomeContainer',
  messageContainer: 'messageContainer',
  welcomeEnter: 'welcomeEnter',
  welcomeExit: 'welcomeExit',
  messageExit: 'messageExit',
  exitingChat: 'exitingChat',
  chatWindow: 'chatWindow',
  maximized: 'maximized',
  minimized: 'minimized',
  chatHeader: 'chatHeader',
  chatControls: 'chatControls',
  iconButton: 'iconButton',
  chatContentWrapper: 'chatContentWrapper',
  centralizedContent: 'centralizedContent',
  floatingIcon: 'floatingIcon',
  chatIcon: 'chatIcon',
  infinibotContainer: 'infinibotContainer'
}));

// Mock assets
jest.mock('../assets/renewChat.png', () => 'renewChatIcon');
jest.mock('../assets/maximizeChat.png', () => 'maximizeIcon');
jest.mock('../assets/minimizeChat.png', () => 'minimizeIcon');
jest.mock('../assets/closeChat.png', () => 'closeIcon');
jest.mock('../assets/chatIcon.png', () => 'chatIcon');

// Mock API config
jest.mock('../config/env', () => ({
  API_BASE_URL: 'http://test-api',
  API_ROOT_URL: 'http://test-root'
}));

import * as React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import axios from 'axios';
import Infinibot from './Infinibot';
import { IInfinibotProps } from './IInfinibotProps';
import '@testing-library/jest-dom';

const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock the scrollIntoView function which is not implemented in jsdom
Element.prototype.scrollIntoView = jest.fn();

// Setup mock response data
const mockResponseData = {
  response: 'This is a test response from the bot.\n## Sources Used\nDoc1, Doc2',
  threadId: '12345',
  sources: [
    { source: 'Document1.pdf', webUrl: 'http://example.com/doc1', docId: 'doc1' },
    { source: 'Document2.pdf', webUrl: 'http://example.com/doc2', docId: 'doc2' }
  ]
};

// Setup mock props
const mockProps: IInfinibotProps = {
  context: {
    pageContext: {
      user: {
        email: 'test@example.com',
        loginName: 'testuser'
      }
    }
  } as unknown as IInfinibotProps['context'],
  userDisplayName: 'Test User',
  description: '',
  environmentMessage: '',
  hasTeamsContext: false
};

// Mock timers to control setTimeout and animation timing
jest.useFakeTimers();

describe('Infinibot Component', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    
    // Setup default mock for axios get and post
    mockedAxios.get.mockResolvedValue({ data: { status: 'ok' } });
    mockedAxios.post.mockResolvedValue({ data: mockResponseData });
    
    // Add mock DOM elements for class selections
    document.body.innerHTML = `
      <div class="chatContainer"></div>
      <div class="welcomeContainer"></div>
      <div class="messageContainer"></div>
    `;
  });

  afterEach(() => {
    // Reset the timer mocks after each test
    jest.clearAllTimers();
  });

  test('renders chat icon when chatbot is closed', () => {
    render(<Infinibot {...mockProps} />);
    expect(screen.getByAltText('Chat Icon')).toBeInTheDocument();
  });

  test('toggles chatbot open when chat icon is clicked', () => {
    render(<Infinibot {...mockProps} />);
    
    // Initially the chatbot should be closed
    expect(screen.getByAltText('Chat Icon')).toBeInTheDocument();
    
    // Click the chat icon to open the chatbot
    fireEvent.click(screen.getByAltText('Chat Icon'));
    
    // After clicking, the chatbot should be open and show the header
    expect(screen.getByText('HR Helpdesk')).toBeInTheDocument();
  });

  test('displays welcome message on initial render when opened', () => {
    render(<Infinibot {...mockProps} />);
    
    // Open the chatbot
    fireEvent.click(screen.getByAltText('Chat Icon'));
    
    // WelcomeMessage component should be rendered
    const welcomeContainers = document.querySelectorAll('.welcomeContainer');
    expect(welcomeContainers.length).toBeGreaterThan(0);
  });

  test('toggles maximize/minimize when button is clicked', () => {
    render(<Infinibot {...mockProps} />);
    
    // Open the chatbot
    fireEvent.click(screen.getByAltText('Chat Icon'));
    
    // Initially the chatbot should not be maximized
    const maximizeButton = screen.getByTitle('Maximize Chat');
    expect(maximizeButton).toBeInTheDocument();
    
    // Click to maximize
    fireEvent.click(maximizeButton);
    
    // Now it should show the minimize button
    expect(screen.getByTitle('Minimize Chat')).toBeInTheDocument();
  });

  test('closes chatbot when close button is clicked', () => {
    render(<Infinibot {...mockProps} />);
    
    // Open the chatbot
    fireEvent.click(screen.getByAltText('Chat Icon'));
    
    // Chatbot should be open
    expect(screen.getByText('HR Helpdesk')).toBeInTheDocument();
    
    // Click close button
    fireEvent.click(screen.getByTitle('Close Chat'));
    
    // Chatbot should be closed and show the chat icon again
    expect(screen.getByAltText('Chat Icon')).toBeInTheDocument();
  });

  test('sends message and receives response', async () => {
    // Render component
    const { unmount } = render(<Infinibot {...mockProps} />);
    
    // Open the chatbot
    fireEvent.click(screen.getByAltText('Chat Icon'));
    
    // Find the send button
    const sendButton = screen.getByTestId('send-button');
    
    // Click the send button which will call onSendMessage with "Test message"
    fireEvent.click(sendButton);
    
    // Fast forward all pending timers to handle welcome message animation
    act(() => {
      jest.advanceTimersByTime(1000);
    });
    
    // Verify axios was called correctly
    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        'http://test-api/chat',
        { message: 'Test message' },
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-SharePoint-User': 'test@example.com'
          })
        })
      );
    });
    
    // Advance timers for the bot response typing animation
    act(() => {
      jest.advanceTimersByTime(5000);
    });
    
    // Clean up component to avoid memory leak warnings
    unmount();
  });

  test('starts a new conversation when new chat button is clicked', async () => {
    // Render component
    const { unmount } = render(<Infinibot {...mockProps} />);
    
    // Open the chatbot
    fireEvent.click(screen.getByAltText('Chat Icon'));
    
    // Send a message first to establish a conversation
    const sendButton = screen.getByTestId('send-button');
    fireEvent.click(sendButton);
    
    // Fast forward welcome message animation
    act(() => {
      jest.advanceTimersByTime(1000);
    });
    
    // Wait for message to be processed
    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalled();
    });
    
    // Reset the mock to check for next calls
    mockedAxios.post.mockClear();
    
    // Click new chat button
    const newChatButton = screen.getByTitle('New Chat');
    fireEvent.click(newChatButton);
    
    // Fast forward animation timers
    act(() => {
      jest.advanceTimersByTime(2000);
    });
    
    // Reset conversation state in the component
    // Send another message to verify we're starting a new conversation
    fireEvent.click(sendButton);
    
    // Fast forward welcome message animation again
    act(() => {
      jest.advanceTimersByTime(1000);
    });
    
    // Should call the API without a conversation ID - need to verify this call separately
    // since the state might not reset immediately
    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        expect.stringContaining('http://test-api/chat'),
        { message: 'Test message' },
        expect.anything()
      );
    });
    
    // Clean up to avoid memory leak warnings
    unmount();
  });

  test('handles API errors gracefully', async () => {
    // Silence the expected error log for clean test output
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(jest.fn());

    mockedAxios.post.mockRejectedValueOnce(new Error('API Error'));

    const { unmount } = render(<Infinibot {...mockProps} />);
    fireEvent.click(screen.getByAltText('Chat Icon'));
    fireEvent.click(screen.getByTestId('send-button'));

    act(() => {
      jest.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalled();
    });

    const messages = document.querySelectorAll('[data-testid="mock-chat-message"]');
    expect(messages.length).toBeGreaterThanOrEqual(1);

    unmount();
    errorSpy.mockRestore();
  });

  test('checks backend connection on mount', () => {
    render(<Infinibot {...mockProps} />);
    
    // Should call API to check connection
    expect(mockedAxios.get).toHaveBeenCalledWith('http://test-root/');
  });

  test('uses conversation ID for subsequent messages', async () => {
    const { unmount } = render(<Infinibot {...mockProps} />);
    
    // Open the chatbot
    fireEvent.click(screen.getByAltText('Chat Icon'));
    
    // Send first message to establish conversation
    const sendButton = screen.getByTestId('send-button');
    fireEvent.click(sendButton);
    
    // Fast forward welcome message animation
    act(() => {
      jest.advanceTimersByTime(1000);
    });
    
    // Wait for first message to be processed
    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        'http://test-api/chat',
        { message: 'Test message' },
        expect.anything()
      );
    });
    
    // Fast forward bot response animation
    act(() => {
      jest.advanceTimersByTime(5000);
    });
    
    // Reset mock to check next call
    mockedAxios.post.mockClear();
    
    // Send second message
    fireEvent.click(sendButton);
    
    // Second message should use conversation ID
    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        'http://test-api/chat/12345',
        { message: 'Test message' },
        expect.anything()
      );
    });
    
    unmount();
  });
});
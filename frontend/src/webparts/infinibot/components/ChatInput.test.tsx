import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ChatInput } from './ChatInput';

describe('ChatInput Component', () => {
  // Basic Rendering Tests
  test('renders input and button', () => {
    render(<ChatInput onSendMessage={jest.fn()} isWaiting={false} />);
    expect(screen.getByPlaceholderText(/type your message/i)).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  test('input is initially empty', () => {
    render(<ChatInput onSendMessage={jest.fn()} isWaiting={false} />);
    const input = screen.getByPlaceholderText(/type your message/i);
    expect(input).toHaveValue('');
  });

  // Functionality Tests
  test('updates input value when typing', () => {
    render(<ChatInput onSendMessage={jest.fn()} isWaiting={false} />);
    const input = screen.getByPlaceholderText(/type your message/i);
    
    fireEvent.change(input, { target: { value: 'test message' } });
    expect(input).toHaveValue('test message');
  });

  test('calls onSendMessage when submitted via button click', () => {
    const mockSend = jest.fn();
    render(<ChatInput onSendMessage={mockSend} isWaiting={false} />);
    
    const input = screen.getByPlaceholderText(/type your message/i);
    const button = screen.getByRole('button');

    fireEvent.change(input, { target: { value: 'hello' } });
    fireEvent.click(button);

    expect(mockSend).toHaveBeenCalledWith('hello');
  });

  test('calls onSendMessage when submitted via form submission (Enter key)', () => {
    const mockSend = jest.fn();
    render(<ChatInput onSendMessage={mockSend} isWaiting={false} />);
    
    const input = screen.getByPlaceholderText(/type your message/i);
    // Get the form element as the parent of the input
    const form = input.closest('form');

    fireEvent.change(input, { target: { value: 'submitted with enter' } });
    if (form) {
      fireEvent.submit(form);
    }

    expect(mockSend).toHaveBeenCalledWith('submitted with enter');
  });

  // Edge Case Tests
  test('does not call onSendMessage when input is empty', () => {
    const mockSend = jest.fn();
    render(<ChatInput onSendMessage={mockSend} isWaiting={false} />);
    
    const button = screen.getByRole('button');
    fireEvent.click(button);

    expect(mockSend).not.toHaveBeenCalled();
  });

  test('does not call onSendMessage when input contains only whitespace', () => {
    const mockSend = jest.fn();
    render(<ChatInput onSendMessage={mockSend} isWaiting={false} />);
    
    const input = screen.getByPlaceholderText(/type your message/i);
    const button = screen.getByRole('button');

    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.click(button);

    expect(mockSend).not.toHaveBeenCalled();
  });

  test('can handle very long messages', () => {
    const mockSend = jest.fn();
    render(<ChatInput onSendMessage={mockSend} isWaiting={false} />);
    
    const input = screen.getByPlaceholderText(/type your message/i);
    const button = screen.getByRole('button');
    const longMessage = 'a'.repeat(1000); // 1000 character message

    fireEvent.change(input, { target: { value: longMessage } });
    fireEvent.click(button);

    expect(mockSend).toHaveBeenCalledWith(longMessage);
  });

  // State Handling Tests
  test('disables button when isWaiting is true', () => {
    render(<ChatInput onSendMessage={jest.fn()} isWaiting={true} />);
    
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  test('disables button when input is empty', () => {
    render(<ChatInput onSendMessage={jest.fn()} isWaiting={false} />);
    
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  test('enables button only when input has content and isWaiting is false', () => {
    const { rerender } = render(<ChatInput onSendMessage={jest.fn()} isWaiting={false} />);
    
    const input = screen.getByPlaceholderText(/type your message/i);
    const button = screen.getByRole('button');
    
    // Initially disabled (empty input)
    expect(button).toBeDisabled();
    
    // Input has content, should be enabled
    fireEvent.change(input, { target: { value: 'message' } });
    expect(button).not.toBeDisabled();
    
    // Waiting state, should be disabled even with content
    rerender(<ChatInput onSendMessage={jest.fn()} isWaiting={true} />);
    expect(button).toBeDisabled();
  });

  test('shows waiting icon when isWaiting is true', () => {
    render(<ChatInput onSendMessage={jest.fn()} isWaiting={true} />);
    
    // Check for waiting icon alt text
    expect(screen.getByAltText('Waiting')).toBeInTheDocument();
  });

  test('shows send icon when isWaiting is false', () => {
    render(<ChatInput onSendMessage={jest.fn()} isWaiting={false} />);
    
    // Check for send icon alt text
    expect(screen.getByAltText('Send')).toBeInTheDocument();
  });

  // UI Behavior Tests
  test('clears input after successful submission', () => {
    const mockSend = jest.fn();
    render(<ChatInput onSendMessage={mockSend} isWaiting={false} />);
    
    const input = screen.getByPlaceholderText(/type your message/i);
    const button = screen.getByRole('button');

    fireEvent.change(input, { target: { value: 'test message' } });
    fireEvent.click(button);

    expect(input).toHaveValue('');
  });

  // Accessibility Tests
  test('input and button have proper accessibility attributes', () => {
    render(<ChatInput onSendMessage={jest.fn()} isWaiting={false} />);
    
    const input = screen.getByPlaceholderText(/type your message/i);
    const button = screen.getByRole('button');
    
    expect(input).toHaveAttribute('type', 'text');
    expect(button).toHaveAttribute('type', 'submit');
    expect(button.querySelector('img')).toHaveAttribute('alt');
    expect(button.querySelector('img')).toHaveAttribute('title');
  });
});
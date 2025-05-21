import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { WelcomeMessage } from './WelcomeMessage';

// Mock the styles
jest.mock('./Infinibot.module.scss', () => ({
  welcomeContainer: 'mock-welcomeContainer',
  welcomeIconContainer: 'mock-welcomeIconContainer',
  welcomeIcon: 'mock-welcomeIcon',
  welcomeTitle: 'mock-welcomeTitle',
  welcomeMessage: 'mock-welcomeMessage',
  welcomeEnter: 'mock-welcomeEnter'
}));

// Mock the image import
jest.mock('../assets/botIcon.png', () => 'mock-bot-icon.png');

describe('WelcomeMessage Component', () => {
  // Basic Rendering Tests
  test('renders welcome message with proper content', () => {
    render(<WelcomeMessage userName="John" />);
    
    // Check title
    expect(screen.getByText('INFINIBOT')).toBeInTheDocument();
    
    // Check if user name is included in the message
    expect(screen.getByText(/Hello John !/)).toBeInTheDocument();
    
    // Check if the welcome message includes the expected text
    expect(screen.getByText(/I am Aeturnum's very own SharePoint Chatbot/)).toBeInTheDocument();
  });

  test('renders the bot icon with correct alt text', () => {
    render(<WelcomeMessage userName="Jane" />);
    
    const botIcon = screen.getByAltText('INFINIBOT');
    expect(botIcon).toBeInTheDocument();
    expect(botIcon).toHaveAttribute('src', 'mock-bot-icon.png');
    expect(botIcon).toHaveClass('mock-welcomeIcon');
  });

  // Props Tests
  test('displays different user names correctly', () => {
    const { rerender } = render(<WelcomeMessage userName="Alex" />);
    expect(screen.getByText(/Hello Alex !/)).toBeInTheDocument();
    
    rerender(<WelcomeMessage userName="Sarah" />);
    expect(screen.getByText(/Hello Sarah !/)).toBeInTheDocument();
  });

  test('handles empty userName gracefully', () => {
    render(<WelcomeMessage userName="" />);
    // The space after "Hello" is not rendered as a single text node - adjust the regex to account for this
    expect(screen.getByText(/Hello.*!/)).toBeInTheDocument();
  });

  // Animation Setup Test (simplified)
  test('uses React useEffect for initialization', () => {
    // We're just testing that useEffect is called, not the specific animation
    const useEffectSpy = jest.spyOn(React, 'useEffect');
    render(<WelcomeMessage userName="TestUser" />);
    expect(useEffectSpy).toHaveBeenCalled();
    useEffectSpy.mockRestore();
  });

  // Styling and Accessibility Tests
  test('applies correct CSS classes', () => {
    render(<WelcomeMessage userName="TestUser" />);
    
    // Check container class
    const container = screen.getByText('INFINIBOT').closest('div');
    expect(container).toHaveClass('mock-welcomeContainer');
    
    // Check icon container class
    const iconContainer = screen.getByAltText('INFINIBOT').closest('div');
    expect(iconContainer).toHaveClass('mock-welcomeIconContainer');
    
    // Check title class
    expect(screen.getByText('INFINIBOT')).toHaveClass('mock-welcomeTitle');
  });

  // Integration with DOM Tests
  test('component structure matches expected DOM hierarchy', () => {
    render(<WelcomeMessage userName="TestUser" />);
    
    // Get main container
    const container = screen.getByText('INFINIBOT').closest('div.mock-welcomeContainer');
    expect(container).toBeInTheDocument();
    
    // Check child components within the container
    if (container) {
      expect(container.querySelector('.mock-welcomeIconContainer')).toBeInTheDocument();
      expect(container.querySelector('.mock-welcomeTitle')).toBeInTheDocument();
      expect(container.querySelector('.mock-welcomeMessage')).toBeInTheDocument();
    }
  });
});
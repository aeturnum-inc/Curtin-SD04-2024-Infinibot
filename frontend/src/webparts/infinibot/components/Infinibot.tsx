import * as React from 'react';
import axios from 'axios';
import styles from './Infinibot.module.scss';
import { API_BASE_URL, API_ROOT_URL } from '../config/env';
import { IInfinibotProps } from './IInfinibotProps';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { WelcomeMessage } from './WelcomeMessage';
import renewChatIcon from '../assets/renewChat.png'
import maximizeIcon from '../assets/maximizeChat.png';
import minimizeIcon from '../assets/minimizeChat.png';
import closeIcon from '../assets/closeChat.png';
import chatIcon from '../assets/chatIcon.png';

// Constants for animation and timing
const TYPING_SPEED_MS = 15;
const MIN_TYPING_DURATION_MS = 500;
const MESSAGE_ANIMATION_DELAY_MS = 50;
const CHAT_RESET_DELAY_MS = 400;
const WELCOME_ANIMATION_DURATION_MS = 500;

// Interface for document source
interface DocSource {
  source: string;
  webUrl: string;
  docId: string;
}

// Updated message interface to include timestamp and document sources
interface Message {
  text: string;
  isUser: boolean;
  timestamp: Date;
  isTyping?: boolean; // To indicate if bot is giving out the message
  isSearching?: boolean; // To indicate if bot is searching
  docSources?: DocSource[]; // Array of document sources
}

interface IInfinibotState {
  messages: Array<Message>;
  isOpen: boolean;
  isMaximized: boolean;
  loading: boolean;
  currentConversationId: string | undefined;
  isFirstInteraction: boolean; // Track if this is the first interaction
  showWelcome: boolean; // Control welcome message visibility
  waiting: boolean; // Track when waiting for bot response
  cancelTokenSource?: AbortController; // Add this to manage request cancellation
}

export default class Infinibot extends React.Component<IInfinibotProps, IInfinibotState> {
  private chatContainerRef = React.createRef<HTMLDivElement>();

  // Helper methods for DOM element caching
  private getChatContainer = (): Element | null => {
    return document.querySelector(`.${styles.chatContainer}`);
  }

  private getWelcomeElement = (): Element | null => {
    return document.querySelector(`.${styles.welcomeContainer}`);
  }

  private getMessageElements = (): NodeListOf<Element> => {
    return document.querySelectorAll(`.${styles.messageContainer}`);
  }
  constructor(props: IInfinibotProps) {
    super(props);

    this.state = {
      messages: [],
      isOpen: false,
      isMaximized: false,
      loading: false,
      currentConversationId: undefined,
      isFirstInteraction: true,
      showWelcome: true, // Initially show welcome message
      waiting: false // Intially not waiting for bot response
    };
  }

  componentDidMount(): void {
    // Optional: Check if connection works when component mounts
    this.checkBackendConnection().catch(error => {
      console.error("Backend connection check failed:", error);
    });
  }

  componentDidUpdate(prevProps: IInfinibotProps, prevState: IInfinibotState): void {
    // Scroll to bottom when new messages are added
    if (prevState.messages.length !== this.state.messages.length) {
      this.scrollToBottom();
    }
  }

  private checkBackendConnection = async (): Promise<void> => {
    try {
      const response = await axios.get(`${API_ROOT_URL}/`);
      console.log("Backend connection:", response.data);
    } catch (error) {
      console.error("Backend connection error:", error);
    }
  };

  private scrollToBottom = (): void => {
    if (this.chatContainerRef.current) {
      this.chatContainerRef.current.scrollTop = this.chatContainerRef.current.scrollHeight;
    }
  };

  // Function to remove the "Sources Used" section from the response text
  private cleanResponseText = (text: string): string => {
    // Pattern to match "## Sources Used" section and everything after it
    const sourcesPattern = /## Sources Used[\s\S]*$/;
    return text.replace(sourcesPattern, '').trim();
  };

  private sendMessage = async (message: string): Promise<void> => {
    // Set waiting state to true when sending a message
    this.setState({ waiting: true });

    // If this is the first message, animate the welcome message out
    if (this.state.isFirstInteraction) {
      // First add the "exit" animation class to the welcome message
      const welcomeElement = this.getWelcomeElement();
      if (welcomeElement) {
        // Remove enter class if it exists
        welcomeElement.classList.remove(styles.welcomeEnter);
        // Add exit class
        welcomeElement.classList.add(styles.welcomeExit);
      }

      // Wait for the animation to complete before changing state
      setTimeout(() => {
        this.setState({
          isFirstInteraction: false,
          showWelcome: false // Hide welcome message after animation
        });

        // Add user message after welcome message is hidden
        this.setState(prevState => ({
          messages: [...prevState.messages, {
            text: message,
            isUser: true,
            timestamp: new Date()
          }]
        }), () => {
          // Continue with the rest of the message handling
          this.handleMessageProcessing(message).catch(error => {
            console.error("Error processing message:", error);
          });
        });
      }, WELCOME_ANIMATION_DURATION_MS);
    } else {
      // Normal flow for subsequent messages
      this.setState(prevState => ({
        messages: [...prevState.messages, {
          text: message,
          isUser: true,
          timestamp: new Date()
        }]
      }), () => {
        this.handleMessageProcessing(message).catch(error => {
          console.error("Error processing message:", error);
        });
      });
    }
  };

  // Separate the API call logic into its own method
  private handleMessageProcessing = async (message: string): Promise<void> => {
    // Cancel any previous request if it exists
    if (this.state.cancelTokenSource) {
      this.state.cancelTokenSource.abort(); // Abort the previous request
    }

    // Create a new AbortController
    const abortController = new AbortController();
    this.setState({ cancelTokenSource: abortController });
    try {
      // First add an empty "searching" message from the bot
      this.setState(prevState => ({
        messages: [...prevState.messages, {
          text: "",
          isUser: false,
          timestamp: new Date(),
          isTyping: false,
          isSearching: true
        }]
      }));
  
      // Get the user's email from SharePoint context
      const userEmail = this.props.context.pageContext.user.email ||
        this.props.context.pageContext.user.loginName ||
        this.props.userDisplayName;
  
      console.log("User identity being sent:", userEmail);
  
      let response = null;
  
      // Call the appropriate endpoint based on whether we have a conversation ID
      if (!this.state.currentConversationId) {
        // Use Axios with the proper headers
        response =         response = await axios.post(
          `${API_BASE_URL}/chat`,
          {
            message,
          },
          {
            headers: {
              "Content-Type": "application/json",
              "X-SharePoint-User": userEmail,
              "X-User-Email": userEmail,
              "X-Dev-Mode": "true" //  this for development
            },
            signal: abortController.signal // Attach the abort signal
          }
        );
      } else {
        response = await axios.post(
          `${API_BASE_URL}/chat/${this.state.currentConversationId}`,
          {
            message,
          },
          {
            headers: {
              "Content-Type": "application/json",
              "X-SharePoint-User": userEmail,
              "X-User-Email": userEmail,
              "X-Dev-Mode": "true" //  this for development
            },
            signal: abortController.signal // Attach the abort signal
          }
        );
      }
  
      const responseData = response.data;
      console.log("Response from backend:", responseData);
  
      const rawResponseText = responseData.response;
      console.log("Raw response:", rawResponseText);
      
      // Clean the response text to remove "Sources Used" section
      const cleanedResponseText = this.cleanResponseText(rawResponseText);
      
      // Extract document sources if available
      const docSources = responseData.sources || [];
      console.log("Document sources:", docSources);
            
      // Store conversation ID if this is a new conversation
      if (!this.state.currentConversationId && responseData.threadId) {
        this.setState({ currentConversationId: responseData.threadId });
      }
  
      // Replace the searching message with typing message
      this.setState(prevState => ({
        messages: prevState.messages.map((msg, index) => {
          if (index === prevState.messages.length - 1) {
            return {
              text: cleanedResponseText,
              isUser: false,
              timestamp: new Date(),
              isTyping: true,
              isSearching: false,
              docSources: docSources // Add document sources to the message
            };
          }
          return msg;
        })
      }));
  
      // After animation completes, mark message as no longer typing
      setTimeout(() => {
        this.setState(prevState => ({
          messages: prevState.messages.map((msg, index) => {
            if (index === prevState.messages.length - 1) {
              return { ...msg, isTyping: false };
            }
            return msg;
          }),
          waiting: false // Set waiting to false when response is complete
        }));
      }, cleanedResponseText.length * TYPING_SPEED_MS + MIN_TYPING_DURATION_MS); // Basic calculation for animation time
  
    } catch (error) {
      if (error.name === "AbortError") {
        console.log("Request aborted:", error.message);
      } else {
        console.error("Error sending message:", error);
        this.setState(prevState => ({
          messages: [...prevState.messages.slice(0, -1), {
            text: "Error occurred. Please try again.",
            isUser: false,
            timestamp: new Date(),
            isSearching: false,
            isTyping: false
          }],
          waiting: false // Set waiting to false when there is an error
        }));
      }
    }
  };

  private toggleChatbot = (): void => {
    this.setState(prevState => ({
      isOpen: !prevState.isOpen,
      isMaximized: false,
      showWelcome: !prevState.isOpen && prevState.messages.length === 0 ? true : prevState.showWelcome,
      isFirstInteraction: !prevState.isOpen && prevState.messages.length === 0 ? true : prevState.isFirstInteraction
    }));

    // If opening the chatbot and no messages yet, ensure welcome state is set
    if (!this.state.isOpen && this.state.messages.length === 0) {
      this.setState({
        showWelcome: true,
        isFirstInteraction: true
      });
    }
  };

  private toggleMaximize = (): void => {
    this.setState(prevState => ({ isMaximized: !prevState.isMaximized }));
  };

  private startNewConversation = (): void => {
    // Cancel any ongoing API requests
    if (this.state.cancelTokenSource) {
      this.state.cancelTokenSource.abort(); // Abort the previous request
    }
    this.setState({ waiting: false });

    // Get all message elements
    const messageElements = this.getMessageElements();

    if (messageElements.length > 0) {
      // Add a custom class to the parent container to control first-child animation
      const chatContainer = this.getChatContainer();
      if (chatContainer) {
        chatContainer.classList.add(styles.exitingChat);
      }

      // Add exit animation class to all messages
      messageElements.forEach((element, index) => {
        // For staggered effect
        setTimeout(() => {
          element.classList.add(styles.messageExit);
        }, index * MESSAGE_ANIMATION_DELAY_MS);
      });

      // Wait for animation to complete before showing welcome message
      setTimeout(() => {
        // Reset state
        this.setState({
          messages: [],
          currentConversationId: undefined,
          showWelcome: true,
          isFirstInteraction: true,
          cancelTokenSource: undefined // Reset the abort controller
        }, () => {
          // After state is updated and welcome component is rendered, animate it in
          setTimeout(() => {
            const welcomeElement = this.getWelcomeElement();
            if (welcomeElement) {
              welcomeElement.classList.add(styles.welcomeEnter);
            }

            // Remove the exiting class from chat container
            const chatContainer = this.getChatContainer();
            if (chatContainer) {
              chatContainer.classList.remove(styles.exitingChat);
            }
          }, MESSAGE_ANIMATION_DELAY_MS);
        });
      }, messageElements.length * MESSAGE_ANIMATION_DELAY_MS + CHAT_RESET_DELAY_MS);
    } else {
      // If there are no messages, just reset state directly
      this.setState({
        messages: [],
        currentConversationId: undefined,
        showWelcome: true,
        isFirstInteraction: true,
        cancelTokenSource: undefined // Reset the abort controller
      });
    }
  };

  public render(): React.ReactElement<IInfinibotProps> {
    const { isOpen, isMaximized, loading, showWelcome, messages, waiting } = this.state;

    return (
      <div className={styles.infinibotContainer}>
        {!isOpen && (
          <div className={styles.floatingIcon} onClick={this.toggleChatbot}>
            <img src={chatIcon} alt="Chat Icon" className={styles.chatIcon} />
          </div>
        )}
        {isOpen && (
          <div className={`${styles.chatWindow} ${isMaximized ? styles.maximized : styles.minimized}`}>
            <div className={styles.chatHeader}>
              <h2>HR Helpdesk</h2>
              <div className={styles.chatControls}>
                <button onClick={this.startNewConversation}>
                  <img
                    src={renewChatIcon}
                    alt="New Chat"
                    title="New Chat"
                    className={styles.iconButton}
                  />
                </button>
                <button onClick={this.toggleMaximize}>
                  <img
                    src={this.state.isMaximized ? minimizeIcon : maximizeIcon}
                    alt={this.state.isMaximized ? "Minimize" : "Maximize"}
                    title={this.state.isMaximized ? "Minimize Chat" : "Maximize Chat"}
                    className={styles.iconButton}
                  />
                </button>
                <button onClick={this.toggleChatbot}>
                  <img
                    src={closeIcon}
                    alt="Close"
                    title="Close Chat"
                    className={styles.iconButton}
                  />
                </button>
              </div>
            </div>

            <div className={`${styles.chatContentWrapper} ${isMaximized ? styles.centralizedContent : ''}`}>
              <div className={styles.chatContainer} ref={this.chatContainerRef}>
                {loading && <div>Loading...</div>}

                {showWelcome ? (
                  <WelcomeMessage userName={this.props.userDisplayName} />
                ) : (
                  messages.map((msg, index) => (
                    <ChatMessage
                      key={index}
                      text={msg.text}
                      isUser={msg.isUser}
                      timestamp={msg.timestamp}
                      isTyping={msg.isTyping}
                      isSearching={msg.isSearching}
                      docSources={msg.docSources}
                    />
                  ))
                )}
              </div>

              <ChatInput onSendMessage={this.sendMessage} isWaiting={waiting} />
            </div>
          </div>
        )}
      </div>
    );
  }
}
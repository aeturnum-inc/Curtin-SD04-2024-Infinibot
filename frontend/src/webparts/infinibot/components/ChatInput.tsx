import * as React from 'react';
import styles from './Infinibot.module.scss';
import sendIcon from '../assets/sendIcon.png';
import waitIcon from '../assets/waitIcon.gif';

interface IChatInputProps {
  onSendMessage: (message: string) => void;
  isWaiting: boolean;
}

export const ChatInput: React.FC<IChatInputProps> = ({ onSendMessage, isWaiting }) => {
  const [message, setMessage] = React.useState('');

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    if (message.trim() && !isWaiting) {
      onSendMessage(message);
      setMessage('');
    }
  };

  return (
    <form className={styles.inputForm} onSubmit={handleSubmit}>
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Type your message here..."
        className={styles.inputField}
      />
      <button 
        type="submit" 
        className={`${styles.sendButton} ${isWaiting ? styles.waitingButton : ''}`}
        disabled={isWaiting || !message.trim()}
      >
        <img 
          src={isWaiting ? waitIcon : sendIcon} 
          alt={isWaiting ? "Waiting" : "Send"}
          title={isWaiting ? "Waiting for response" : "Send"}
          style={{ backgroundColor: isWaiting ? '#ffffff' : 'transparent' }}
        />
      </button>
    </form>
  );
};

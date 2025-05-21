import * as React from 'react';
import styles from './Infinibot.module.scss';
import botIcon from '../assets/botIcon.png';
import { WelcomeMessageProps } from './IInfinibotProps';

export const WelcomeMessage: React.FC<WelcomeMessageProps> = ({ userName }) => {
  const welcomeRef = React.useRef<HTMLDivElement>(null);

  // Add the enter animation class when component mounts
  React.useEffect(() => {
    // Small delay to ensure DOM is ready
    const animationTimer = setTimeout(() => {
      if (welcomeRef.current) {
        welcomeRef.current.classList.add(styles.welcomeEnter);
      }
    }, 100);
    
    return () => clearTimeout(animationTimer);
  }, []);

  return (
    <div className={styles.welcomeContainer} ref={welcomeRef}>
      <div className={styles.welcomeIconContainer}>
        <img src={botIcon} alt="INFINIBOT" className={styles.welcomeIcon} />
      </div>
      <h3 className={styles.welcomeTitle}>INFINIBOT</h3>
      <div className={styles.welcomeMessage}>
        Hello {userName} !
        <br />
        I am Aeturnum&apos;s very own SharePoint Chatbot, INFINIBOT! Here to help you with any questions you have about HR! Please enter your question below to start this conversation!
      </div>
    </div>
  );
};
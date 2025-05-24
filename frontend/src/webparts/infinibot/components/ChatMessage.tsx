import * as React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

import styles from './Infinibot.module.scss';
import botIcon from '../assets/botIcon.png';
import botChattingIcon from '../assets/botChattingIcon.gif';
import botSearchingIcon from '../assets/botSearchingIcon.gif';
import documentIcon from '../assets/documentIcon.png';

interface DocSource {
  source: string;
  webUrl: string;
  docId: string;
}

interface IChatMessageProps {
  text: string;
  isUser: boolean;
  timestamp: Date;
  isTyping?: boolean;
  isSearching?: boolean;
  docSources?: DocSource[];
}

export const ChatMessage: React.FC<IChatMessageProps> = ({
  text,
  isUser,
  timestamp,
  isTyping,
  isSearching,
  docSources
}) => {
  const formatTime = (date: Date): string =>
    date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const [displayedText, setDisplayedText] = React.useState('');
  const [charIndex, setCharIndex] = React.useState(0);

  React.useEffect(() => {
    if (isTyping && !isUser && charIndex < text.length) {
      const timer = setTimeout(() => {
        setDisplayedText(text.substring(0, charIndex + 1));
        setCharIndex(charIndex + 1);
      }, 15);
      return () => clearTimeout(timer);
    } else if (!isTyping || isUser) {
      setDisplayedText(text);
    }
  }, [isTyping, charIndex, text, isUser]);

  React.useEffect(() => {
    setCharIndex(0);
    setDisplayedText(isTyping && !isUser ? '' : text);
  }, [text, isTyping, isUser]);

  const getBotIcon = (): string => {
    if (isSearching) return botSearchingIcon;
    if (isTyping) return botChattingIcon;
    return botIcon;
  };

  const renderDocSources = (): React.ReactNode => {
    if (!docSources || docSources.length === 0) return null;

    return (
      <div className={styles.docSourcesContainer}>
        <div className={styles.docSourcesLabel}>Sources:</div>
        <div className={styles.docSourcesButtons}>
          {docSources.map((doc, index) => (
            <a
              key={index}
              href="#"
              onClick={(e) => {
                e.preventDefault();
                window.open(doc.webUrl, '_blank', 'noopener,noreferrer');
              }}
              className={styles.docSourceButton}
              title={`View document: ${doc.source}`}
            >
              <img src={documentIcon} alt="Document" className={styles.docIcon} />
              <span className={styles.docName}>{doc.source}</span>
            </a>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className={`${styles.messageWrapper} ${isUser ? styles.userMessageWrapper : ''}`}>
      <div className={`${styles.messageContainer} ${isUser ? styles.userMessageContainer : ''}`}>
        {!isUser && (
          <div className={styles.icon}>
            <img src={getBotIcon()} alt="bot icon" />
          </div>
        )}

        <div className={`${styles.textContainer} ${isUser ? styles.userTextContainer : ''}`}>
          <div className={`${styles.nameTimeContainer} ${isUser ? styles.userNameTimeContainer : ''}`}>
            {!isUser && <span className={styles.name}>INFINIBOT</span>}
            <span className={styles.timestamp}>{formatTime(timestamp)}</span>
          </div>

          <div className={`${styles.message} ${isUser ? styles.userMessage : styles.botMessage}`}>
            <div className={styles.markdownContainer}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeRaw]}
                components={{
                  p: ({ node, ...props }) => <p className={styles.mdParagraph} {...props} />,
                  strong: ({ node, ...props }) => <strong className={styles.mdStrong} {...props} />,
                  em: ({ node, ...props }) => <em className={styles.mdItalic} {...props} />,
                  ul: ({ node, ...props }) => <ul className={styles.mdUnorderedList} {...props} />,
                  ol: ({ node, ...props }) => <ol className={styles.mdOrderedList} {...props} />,
                  li: ({ node, ...props }) => <li className={styles.mdListItem} {...props} />,
                  table: ({ node, ...props }) => <table className={styles.mdTable} {...props} />,
                  thead: ({ node, ...props }) => <thead className={styles.mdThead} {...props} />,
                  tbody: ({ node, ...props }) => <tbody className={styles.mdTbody} {...props} />,
                  tr: ({ node, ...props }) => <tr className={styles.mdTr} {...props} />,
                  th: ({ node, ...props }) => <th className={styles.mdTh} {...props} />,
                  td: ({ node, ...props }) => <td className={styles.mdTd} {...props} />,
                  a: ({ node, ...props }) => (
                    <a className={styles.mdLink} target="_blank" rel="noopener noreferrer" {...props} />
                  ),
                }}
              >
                {isTyping && !isUser ? displayedText : text}
              </ReactMarkdown>
            </div>
            {!isUser && docSources && docSources.length > 0 && (
              <>
                <hr className={styles.divider} />
                {renderDocSources()}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

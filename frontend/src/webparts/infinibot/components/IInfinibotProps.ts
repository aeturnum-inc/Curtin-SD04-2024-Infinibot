import { WebPartContext } from '@microsoft/sp-webpart-base';

export interface IInfinibotProps {
  description: string;
  environmentMessage: string;
  hasTeamsContext: boolean;
  userDisplayName: string;
  context: WebPartContext;
}

// New props for WelcomeMessage
export interface WelcomeMessageProps {
  userName: string;
}
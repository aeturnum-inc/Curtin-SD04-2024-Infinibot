import * as React from 'react';
import * as ReactDom from 'react-dom';
import { Version } from '@microsoft/sp-core-library';
import {
  IPropertyPaneConfiguration,
  PropertyPaneTextField
} from '@microsoft/sp-property-pane';
import { BaseClientSideWebPart } from '@microsoft/sp-webpart-base';
import { IReadonlyTheme } from '@microsoft/sp-component-base';

import * as strings from 'InfinibotWebPartStrings';
import Infinibot from './components/Infinibot';
import { IInfinibotProps } from './components/IInfinibotProps';

export interface IInfinibotWebPartProps {
  description: string;
}

export default class InfinibotWebPart extends BaseClientSideWebPart<IInfinibotWebPartProps> {
  private _environmentMessage: string = '';

  public render(): void {
    const element: React.ReactElement<IInfinibotProps> = React.createElement(
      Infinibot,
      {
        description: this.properties.description,
        environmentMessage: this._environmentMessage,
        hasTeamsContext: !!this.context.sdks.microsoftTeams,
        userDisplayName: this.context.pageContext.user.displayName,
        context: this.context // Pass the SPFx context which contains user identity and http client
      }
    );

    ReactDom.render(element, this.domElement);
  }

  protected onInit(): Promise<void> {
    return this._getEnvironmentMessage().then(message => {
      this._environmentMessage = message;
    });
  }

  private _getEnvironmentMessage(): Promise<string> {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (this.context.sdks.microsoftTeams) {
          resolve('This WebPart is running in Microsoft Teams!');
        } else {
          resolve('This WebPart is running in SharePoint.');
        }
      }, 1000);
    });
  }

  protected onThemeChanged(currentTheme: IReadonlyTheme | undefined): void {
    // No theme changes are necessary
  }

  protected onDispose(): void {
    ReactDom.unmountComponentAtNode(this.domElement);
  }

  protected get dataVersion(): Version {
    return Version.parse('1.0');
  }

  protected getPropertyPaneConfiguration(): IPropertyPaneConfiguration {
    return {
      pages: [
        {
          header: {
            description: strings.PropertyPaneDescription
          },
          groups: [
            {
              groupName: strings.BasicGroupName,
              groupFields: [
                PropertyPaneTextField('description', {
                  label: strings.DescriptionFieldLabel
                })
              ]
            }
          ]
        }
      ]
    };
  }
}
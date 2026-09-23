import * as amplitude from "@amplitude/analytics-browser";
import { sessionReplayPlugin } from '@amplitude/plugin-session-replay-browser';

const AMPLITUDE_API_KEY = "3179f06cf5abac32ea4e17d68733ef2f";

export const initializeAmplitude = (): void => {
    amplitude.init(AMPLITUDE_API_KEY, {
        logLevel: amplitude.Types.LogLevel.Warn,
        defaultTracking: { sessions: true },
    });
};

// use these generic event types for tracking
// usage: logEvent(EVENT.CLICK, properties)
export const EVENT = {
    CLICK: "click",
    SELECT: "select",
    SUBMIT: "submit",
    SIGN_IN: "sign_in",
    SIGN_OUT: "sign_out",
}

// use these as event names for tracking
// usage: properties.event_name = EVENT_NAME.CHATBOT.OPEN
export const EVENT_NAME = {
    CHATBOT: {
        OPEN: "chatbot_open",
        CLOSE: "chatbot_close",
        CATEGORY_SELECT: "chatbot_category_select",
        QUESTION: "chatbot_question",
        RESET: "chatbot_reset",
    },
    ANALYTICS_PAGE: {
        DATA_SOURCE_TOGGLE: "analytics_data_source_select",
        CHART_TOGGLE: "analytics_chart_toggle",
        SET_FILTER: "analytics_set_filter",
        DRAG_CHART: "analytics_drag_chart",
    },
    AUTH: {
        CLOSE_MODAL: "auth_close_modal",
        OPEN_MODAL: "auth_open_modal",
    },
    EMAIL_CAPTURE: {
        OPEN_MODAL: "email_capture_open_modal",
        CLOSE_MODAL: "email_capture_close_modal",
        SUBMIT: "email_capture_submit",
    },
    NAVBAR: {
        TOGGLE_DRAWER: "navbar_toggle_drawer",
    }
}

export const logEvent = (eventName: string, properties?: object): void => {
    console.log({eventName, properties})
    const path = window.location.pathname + window.location.search;
    amplitude?.logEvent(eventName, {...properties, path});
};

// Create and Install Session Replay Plugin
const sessionReplayTracking = sessionReplayPlugin({sampleRate: 1});
amplitude.add(sessionReplayTracking);

export const identifyUserEmail = (email: string): void => {
    const identifyEvent = new amplitude.Identify();
    identifyEvent.set('demo_email', email);
    amplitude.identify(identifyEvent);
}


import axios from "axios";
import * as React from "react";
import { StyleSheet, css } from "aphrodite";
import ChatBubble, { ChatBubbleProps } from "./ChatBubble";
import { CircularProgress } from "@mui/material";

import Button from "../Button/Button";
import BlockhouseInput from "../BlockhouseInput/BlockhouseInput";
import BouncingDots from "../BouncingDots/BouncingDots";
import close from "../../Assets/icons/close.svg";
import send from "../../Assets/icons/send.svg";
import { EVENT_NAME, EVENT, logEvent } from "../../utils/analytics";
interface ChatOverlayProps {
    file_id: string;
    onClose: () => void;
}

const InitializingState: React.FC = () => {
    return (
        <div className={css(styles.initializingChat)}>
            <CircularProgress color="inherit" />
            <p>Initializing chat, Please hang on..</p>
        </div>
    );
};

const AssistantTyping: React.FC = () => {
    return (
        <div className={css(styles.assistantTyping)}>
            <BouncingDots />
            <p>Blockhouse is typing...</p>
        </div>
    );
};
const userCategories = [
    { key: "compliance", value: "Compliance" },
    { key: "portfolio_manager", value: "Portfolio Manager" },
    { key: "trader_bonds", value: "Trader - Bonds" },
    { key: "trader_crypto", value: "Trader - Crypto" }
]
const ChatOverlay: React.FC<ChatOverlayProps> = ({ file_id, onClose }) => {
    const [category, _setCategory] = React.useState<string>("");
    const setCategory = (category: string) => {
        _setCategory(category);
        // track only while setting or changing category
        if (category) {
            logEvent(EVENT.CLICK, { event_name: EVENT_NAME.CHATBOT.CATEGORY_SELECT, chat_category: category });
        }
    }
    const [questionCount, setQuestionCount] = React.useState<number>(0);
    const [initialQuestions, setInitialQuestions] = React.useState<String[]>(
        []
    );
    React.useEffect(() => {
        setTimeout(() => {
            setInitialQuestions(userCategories.map(category => category.value));
        }, 1500);
    }, []);
    const [messages, setMessages] = React.useState<
        ChatBubbleProps[] | undefined
    >(undefined);
    const [inputMessage, setInputMessage] = React.useState<string>("");

    const [questionIndex, setQuestionIndex] = React.useState<number>(0);
    const [initializing, setinitializing] = React.useState<boolean>(false);
    const [assistantTyping, setAssistantTyping] =
        React.useState<boolean>(false);

    const [hasInitialQuestionClicked, setHasInitialQuestionClicked] = React.useState<boolean>(false);
    const [showResetButton, setShowResetButton] = React.useState<boolean>(false);

    const conversationEndRef = React.useRef<HTMLDivElement>(null); // Ref for automatic scrolling

    const scrollToBottom = () => {
        conversationEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };
    const resetChat = () => {
        setCategory("")
        setMessages([]);
        setInitialQuestions(userCategories.map(category => category.value));
        setQuestionIndex(0);
        setQuestionCount(0);
        setShowResetButton(false);
        logEvent(EVENT.CLICK, { event_name: EVENT_NAME.CHATBOT.RESET });
    }
    const handleSendMessage = async (question: string, is_question: boolean = false) => {
        const selectedCategory = userCategories.find(category => category.value === question);
        const message: ChatBubbleProps = {
            type: "text",
            chart_type: null,
            data: question,
            sender: "user",
        };
        if (!category && selectedCategory) {
            setCategory(selectedCategory.key);
            is_question = true
            setHasInitialQuestionClicked(true);
        } else {
            if (!is_question) {
                setMessages((prevMessages) => [...(prevMessages || []), message]);
            }
        }
        setInitialQuestions([]);
        setAssistantTyping(true);

        try {
            if (!is_question) {

            }
            const response = await axios.post(
                "/api/chat/get_response/",
                {
                    category: category || selectedCategory?.key,
                    question_index: questionIndex,
                    file_id: file_id,
                    is_question
                },
                {
                    // headers: {
                    //     Authorization: `Bearer ${token}`,
                    // },
                }
            );
            if (response.status !== 200) {
                throw new Error(response.data.error);
            }
            if (is_question) {
                response.data.data.map((item: ChatBubbleProps) => {
                    setInitialQuestions((prevQuestions) => [...prevQuestions, item.data]);
                });
            }
            else {
                response.data.data.map((item: ChatBubbleProps) => {
                    setMessages((prevMessages) => [...(prevMessages || []), item]);
                });
                setQuestionIndex(prevQuestionIndex => prevQuestionIndex + 1);
            }
            if (!questionCount) {
                setQuestionCount(response.data.question_count)
            }

        } catch (error) {
            const error_message = (error as any).response?.data?.error;
            console.log(error);
        } finally {
            setAssistantTyping(false);
        }

    };

    React.useEffect(() => {
        // fetch next question add to initial questions after delay
        if (questionIndex !== 0 && questionIndex < questionCount) {
            setTimeout(() => {
                handleSendMessage("", true)
            }, 2000);
        }
    }, [questionIndex])
    React.useEffect(() => {
        if (questionIndex > 0 && questionIndex >= questionCount) {
            setTimeout(() => {
                setShowResetButton(true)
                scrollToBottom()
            }, 2000);
        }
    }, [questionIndex])
    React.useEffect(() => {
        scrollToBottom();
    }, [messages, initialQuestions]);

    const handleKeyDown = (event: React.KeyboardEvent) => {
        if (
            event.key === "Enter" &&
            !event.shiftKey &&
            inputMessage.trim() !== ""
        ) {
            event.preventDefault();
        }
    };

    return (
        <div>
            <div className={css(styles.container)}>
                <div className={css(styles.header)}>
                    <Button
                        buttonType="secondary"
                        customStyles={styles.closeBtn}
                        onClick={onClose}
                    >
                        <img src={close} alt="close" />
                    </Button>
                </div>
                <div className={css(styles.conversation)}>
                    {!category && <ChatBubble type="text" chart_type={null} data="Hello, welcome to the Blockhouse AI assistant. We give you targeted insights into your trading activity. Please click the buttons at the bottom of the screen to progress the conversations. First, we'd like to know what role you're involved in at your organization to provide a relevant set of sample insights" sender="assistant" />}
                    {initializing && <InitializingState />}
                    {messages?.length! > 0
                        && messages!.map(
                            (message: ChatBubbleProps, index: number) => (
                                <ChatBubble
                                    key={index}
                                    type={message.type}
                                    chart_type={message.chart_type}
                                    data={message.data}
                                    sender={message.sender}
                                />
                            )
                        )}
                    <div ref={conversationEndRef} />
                </div>
                <div
                    className={css(
                        styles.initialQuestionContainer
                    )}
                >
                    {initialQuestions.map((question) => (
                        <Button
                            buttonType="secondary"
                            key={question as string}
                            customStyles={([styles.initialQuestion, ...(!hasInitialQuestionClicked ? [styles.bounceWithDelay] : [])])}
                            onClick={() => {
                                if (category) {
                                    // this click sets category if category is not set, which is tracked in setCategory
                                    logEvent(EVENT.CLICK, { event_name: EVENT_NAME.CHATBOT.QUESTION, chat_category: category });
                                }
                                handleSendMessage(
                                    question as string
                                )
                            }}
                        >
                            {question}
                        </Button>
                    ))}
                    {showResetButton && <Button buttonType="secondary" customStyles={styles.initialQuestion} onClick={resetChat}>Reset Chat</Button>}
                </div>
                <div className={css(styles.inputContainer)}>
                    {assistantTyping && <AssistantTyping />}
                    <div className={css(styles.inputSection)}>
                        <BlockhouseInput
                            placeholder="Type a message here..."
                            type="text"
                            value={inputMessage}
                            setInput={setInputMessage}
                            fullWidth
                            multiline
                            disabled
                            customStyles={styles.inputStyle}
                            onKeyDown={handleKeyDown}
                        />
                        <Button
                            buttonType="primary"
                            customStyles={styles.sendBtn}
                        >
                            <img src={send} alt="send" />
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ChatOverlay;

const styles = StyleSheet.create({
    container: {
        height: "600px",
        width: "min(60%, 1200px)",
        bottom: 20,
        right: 20,
        position: "fixed",
        display: "flex",
        flexDirection: "column",
        backgroundColor: "#0A0A0A",
        padding: "10px",

        borderRadius: "8px",
        border: "1px solid #222",
        zIndex: 1001,
    },
    header: {
        height: "6%",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "flex-end",
        borderRadius: "10px",
    },
    closeBtn: {
        height: "30px",
        width: "30px",
        padding: 0,
        borderRadius: "8px",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
    },
    conversation: {
        display: "flex",
        flexDirection: "column",
        flexGrow: 1,
        overflowY: "auto",
        padding: "10px",
        marginBottom: "10px",
        height: "80%",
    },
    inputContainer: {
        display: "flex",
        flexDirection: "column",
        padding: "10px",
    },
    assistantTyping: {
        display: "flex",
        flexDirection: "row",
        justifyContent: "flex-start",
        alignItems: "center",
        color: "#797A7A",
        fontSize: "12px",
    },
    inputSection: {
        display: "flex",
        bottom: 0,
        justifyContent: "center",
        alignItems: "flex-end",
    },
    sendBtn: {
        borderRadius: "10%",
        height: "45px",
        width: "45px",
        marginLeft: "10px",
        justifyContent: "center",
        display: "flex",
        alignItems: "center",
    },
    sendIcon: {
        position: "absolute",
        right: "10px",
        bottom: "10px",
        zIndex: 2,
        background: "white",
        height: "16px",
        width: "16px",
        borderRadius: "4px",
        pointerEvents: "none",
    },
    sendImage: {
        width: "16px",
        height: "16px",
    },
    initializingChat: {
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        height: "100%",
    },

    inputStyle: {
        border: "1px solid #1B1B1B",
    },

    initialQuestionContainer: {
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        position: "relative",
        flexDirection: "row"
    },
    initialQuestion: {
        maxWidth: 600,
        minHeight: 60,
        backgroundColor: "#222",
        color: "#ffffffba",
        fontWeight: 300,
        margin: "10px",
        textAlign: "left",
        fontFamily: "inherit",
        fontSize: "16px",
        borderRadius: "20px",
    },
    bounceWithDelay: {
        animationName: "bounceWithDelay",
        animationDuration: "4s",
        animationTimingFunction: "ease",
        animationDelay: "2s",
        animationIterationCount: "infinite",
        animationDirection: "normal",
        animationFillMode: "forwards",
        animationPlayState: "running",
    },
});


import React from "react";
import { css, StyleSheet } from "aphrodite";
import { logEvent } from "../../utils/analytics";

const TermsOfService: React.FC = () => {
    return (
        <div className={css(styles.container)}>
            <h1>Blockhouse Terms of Service</h1>
            <h3>Effective Date: February 6, 2024</h3>
            <hr />
            <p>
                Welcome to Blockhouse! These Terms of Service ("Terms") govern
                your use of our website and services provided through
                https://blockhouse.app (the "Site"). Please read these Terms
                carefully before accessing or using our services.
            </p>

            <ol>
                <li className={css(styles.title2)}>User Eligibility and Account</li>
                <hr />
                <ol>
                    <li className={css(styles.item)}>
                        You must be at least 18 years old to use our services.
                        By accessing or using the Site, you represent and
                        warrant that you are 18 years of age or older.
                    </li>
                    <li className={css(styles.item)}>
                        You are responsible for maintaining the confidentiality
                        of your account credentials and for all activities that
                        occur under your account. You agree to notify us
                        immediately of any unauthorized access or use of your
                        account.
                    </li>
                </ol>

                <li className={css(styles.title2)}>Intellectual Property Rights</li>
                <hr />
                <ol>
                <li className={css(styles.item)}>
                        The Site and its original content, features, and
                        functionality are owned by Blockhouse and are protected
                        by international copyright, trademark, patent, trade
                        secret, and other intellectual property or proprietary
                        rights laws.
                    </li>
                    <li className={css(styles.item)}>
                        You may not use, reproduce, modify, adapt, publish,
                        distribute, publicly display, publicly perform,
                        transmit, or otherwise exploit the Site or its content,
                        except as expressly authorized by Blockhouse.
                    </li>
                </ol>

                <li className={css(styles.title2)}>Prohibited Activities</li>
                <hr />
                <ol>
                    <li>
                        You agree not to engage in any of the following
                        prohibited activities:
                    </li>
                    <ul>
                    <li className={css(styles.item)}>Violating any applicable laws or regulations;</li>
                    <li className={css(styles.item)}>Impersonating any person or entity;</li>
                    <li className={css(styles.item)}>
                            Interfering with or disrupting the integrity or
                            performance of the Site;
                        </li>
                        <li className={css(styles.item)}>
                            Using any automated system, including "robots,"
                            "spiders," or "offline readers," to access the Site;
                        </li>
                        <li className={css(styles.item)}>
                            Collecting or harvesting any personally identifiable
                            information from the Site;
                        </li>
                        <li className={css(styles.item)}>
                            Engaging in any conduct that restricts or inhibits
                            any other user from using or enjoying the Site;
                        </li>
                        <li className={css(styles.item)}>
                            Attempting to gain unauthorized access to our
                            computer systems or engage in any activity that
                            disrupts, diminishes the quality of, interferes with
                            the performance of, or impairs the functionality of
                            the Site;
                        </li>
                        <li className={css(styles.item)}>
                            Using the Site for any illegal, harmful, or
                            unauthorized purpose;
                        </li>
                        <li className={css(styles.item)}>
                            Uploading or transmitting any viruses, malware, or
                            other types of malicious code;
                        </li>
                        <li className={css(styles.item)}>
                            Engaging in any activity that may damage, disable,
                            or overburden the Site;
                        </li>
                        <li className={css(styles.item)}>
                            Violating any third party's rights, including
                            intellectual property or privacy rights;
                        </li>
                        <li className={css(styles.item)}>
                            Using the Site to transmit, distribute, post, or
                            submit any unauthorized or unsolicited promotional
                            materials, spam, or any other form of solicitation;
                        </li>
                        <li className={css(styles.item)}>
                            Using the Site for any fraudulent or deceptive
                            purposes;
                        </li>
                        <li className={css(styles.item)}>
                            Engaging in any activity that could interfere with
                            the operation of the Site or the services provided;
                        </li>
                        <li className={css(styles.item)}>
                            Assisting or encouraging any third party in engaging
                            in any prohibited conduct.
                        </li>
                    </ul>
                </ol>

                <li className={css(styles.title2)}>Third-Party Links and Content</li>
                <hr />
                <p>
                    The Site may contain links to third-party websites or
                    resources. You acknowledge and agree that we are not
                    responsible or liable for the availability, accuracy,
                    content, or policies of third-party websites or resources.
                    Links to such websites or resources do not imply any
                    endorsement by Blockhouse. You acknowledge sole
                    responsibility for and assume all risk arising from your use
                    of any third-party websites or resources.
                </p>

                <li className={css(styles.title2)}>Disclaimer of Warranties</li>
                <hr />
                <p>
                    THE SITE AND SERVICES ARE PROVIDED ON AN "AS IS" AND "AS
                    AVAILABLE" BASIS, WITHOUT ANY WARRANTIES OF ANY KIND,
                    EXPRESS OR IMPLIED. TO THE FULLEST EXTENT PERMITTED BY
                    APPLICABLE LAW, BLOCKHOUSE DISCLAIMS ALL WARRANTIES,
                    INCLUDING, BUT NOT LIMITED TO, IMPLIED WARRANTIES OF
                    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
                    NON-INFRINGEMENT. BLOCKHOUSE DOES NOT WARRANT THAT THE SITE
                    OR SERVICES WILL BE UNINTERRUPTED, ERROR-FREE, OR FREE OF
                    VIRUSES OR OTHER HARMFUL COMPONENTS.
                </p>

                <li className={css(styles.title2)}>Limitation of Liability</li>
                <hr />
                <p>
                    TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, IN NO
                    EVENT SHALL BLOCKHOUSE OR ITS DIRECTORS, OFFICERS,
                    EMPLOYEES, AGENTS, OR AFFILIATES BE LIABLE FOR ANY INDIRECT,
                    INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES,
                    INCLUDING, BUT NOT LIMITED TO, DAMAGES FOR LOSS OF PROFITS,
                    GOODWILL, USE, DATA, OR OTHER INTANGIBLE LOSSES, ARISING OUT
                    OF OR RELATING TO YOUR ACCESS TO OR USE OF, OR YOUR
                    INABILITY TO ACCESS OR USE, THE SITE OR SERVICES, WHETHER
                    BASED ON WARRANTY, CONTRACT, TORT (INCLUDING NEGLIGENCE), OR
                    ANY OTHER LEGAL THEORY, EVEN IF BLOCKHOUSE HAS BEEN ADVISED
                    OF THE POSSIBILITY OF SUCH DAMAGES.
                </p>

                <li className={css(styles.title2)}>Indemnification</li>
                <hr />
                <p>
                    You agree to indemnify, defend, and hold harmless Blockhouse
                    and its directors, officers, employees, agents, and
                    affiliates from and against any and all claims, liabilities,
                    damages, losses, costs, expenses, or fees (including
                    reasonable attorneys' fees) arising from or relating to your
                    use or misuse of the Site or services, your violation of
                    these Terms, or your violation of any rights of a third
                    party.
                </p>

                <li className={css(styles.title2)}>Governing Law and Jurisdiction</li>
                <hr />
                <p>
                    These Terms shall be governed by and construed in accordance
                    with the laws of [Insert Jurisdiction]. Any legal action or
                    proceeding arising out of or relating to these Terms or the
                    Site shall be exclusively brought in the courts of [Insert
                    Jurisdiction], and you consent to the personal jurisdiction
                    of such courts.
                </p>

                <li className={css(styles.title2)}>Changes to Terms</li>
                <hr />
                <p>
                    Blockhouse reserves the right, at its sole discretion, to
                    modify or replace these Terms at any time. If we make
                    material changes to these Terms, we will provide notice
                    through the Site or by other means. Your continued use of
                    the Site following the posting of any changes to these Terms
                    constitutes acceptance of those changes.
                </p>
                <p>
                    If you have any questions about these Terms, please contact
                    us at aaditya@blockhouse.capital.
                </p>
            </ol>
        </div>
    );
};

export default TermsOfService;

const styles = StyleSheet.create({
    container: {
        padding: "20px",
        maxWidth: "800px",
        margin: "auto",
        textAlign: "left",

        "@media (max-width: 800px)": {
            padding: "10px",
        },
    },
    title2: {
        fontSize: "1.5rem",
        // marginBottom: "1rem",
    },

    item: {
        marginBottom: "0.5rem",
    }
});

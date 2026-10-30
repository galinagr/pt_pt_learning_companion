# Hear and say

The page speaks European Portuguese and listens through the browser. The study model is not used. No speech key, token, or password is written into source.

## Start

One button, labeled **Start**, generates the result for the selected action: translation, check, created text, or verb forms. The label stays **Start** for every action. While the result is being prepared, the button and the sheet say **Processing…**. The result stays hidden until Start finishes. Changing the action clears the result until Start is pressed again.

Speaker buttons, word playback, and the practice microphone appear only on the Portuguese result after Start. The microphone beside an input can be used before Start, because it fills that input.

## Hear Portuguese

A speaker button follows every Portuguese sentence in a translation, a check, a created text, and each verb form, including the Portuguese infinitive on the verb sheet. It speaks that sentence in European Portuguese (`pt-PT`). The sheet has a playback speed of **1×** or **0.5×**. Word clicks use the same speed.

Clicking one Portuguese word in those sentences speaks only that word, in the spelling on the screen. Punctuation around the word is not spoken. English sentences, notes, and warnings have no speaker and are not clickable for speech.

Play asks the local page for audio. The voice is the European Portuguese neural voice `pt-PT-RaquelNeural`. The Mac compact voice is not used. The words are spoken in the spelling on the screen. The text is sent to Microsoft's speech service by the `edge-tts` library. This project does not store a speech key. At **0.5×** the request rate is `0.5`. At **1×** the request rate is `1`. If the local page is not running, the sheet says **European Portuguese speech did not start. Open this page from the local server.**

## Say it

A microphone does two jobs.

**Dictate.** A microphone beside the active input writes the transcript into that field, replacing the text that was there. The character limit already on that field still applies.

| Action | Field | Recognition language |
| --- | --- | --- |
| Translate, English to European Portuguese | Text | `en-US` |
| Translate, European Portuguese to English | Text | `pt-PT` |
| Check | Text | `pt-PT` |
| Create a text | Topic | `en-US` |
| Verb forms | Verb | `pt-PT` |

The verb field accepts a typed English or Portuguese verb. Its microphone listens in European Portuguese. An English verb is typed.

**Practice.** Each Portuguese sentence on the result has a practice microphone. The learner says that sentence. Under the sentence, the sheet shows **Heard:** and the transcript. When the words match, it also shows **Matched.** Otherwise it shows **Not the same words.**

A match compares the sentence and the transcript after Unicode NFC, lowercasing, and removing punctuation. Words are split on whitespace. Order matters. Accents matter, so `nao` does not match `não`.

## One sound at a time

Starting playback or recognition cancels whatever was already speaking or listening. Copy, save, and send keep the words only. They omit the buttons and the heard line.

## When the browser cannot do it

| Situation | What the sheet says |
| --- | --- |
| No speech synthesis and no speech recognition | This browser has no voice tools. |
| Microphone permission denied | The microphone is blocked. Allow it in the browser, then try again. |
| Recognition ends with no words | No speech was heard. Try again. |
| Recognition fails for another reason | The field or the heard line is left as it was. |

The page does not store the audio. A browser such as Chrome may send the audio to its own speech service. This project does not add a server route or a key for that.

## Where it lives

The preview at `preview/index.html` is the first place these controls appear, on the sample result. The local page uses the same browser behavior when it is built. There is no `/api` route for speech.

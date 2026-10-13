/**
 * Text typed with the keyboard set to the other language: "9voouh" is "ตอนนี้"
 * on a Thai Kedmanee layout. Each string lists the characters of the same keys,
 * in the same order, on a US layout and on Kedmanee.
 */
const LATIN = "1234567890-=qwertyuiop[]\\asdfghjkl;'zxcvbnm,./" + "!@#$%^&*()_+QWERTYUIOP{}|ASDFGHJKL:\"ZXCVBNM<>?";
const THAI = "ๅ/-ภถุึคตจขชๆไำพะัีรนยบลฃฟหกดเ้่าสวงผปแอิืทมใฝ" + "+๑๒๓๔ู฿๕๖๗๘๙๐\"ฎฑธํ๊ณฯญฐ,ฅฤฆฏโฌ็๋ษศซ.()ฉฮฺ์?ฒฬฦ";

const latinChars = Array.from(LATIN);
const thaiChars = Array.from(THAI);
const toThai = new Map(latinChars.map((char, index) => [char, thaiChars[index]]));
const toLatin = new Map(thaiChars.map((char, index) => [char, latinChars[index]]));

const THAI_SCRIPT = /[฀-๿]/;

/** The same keystrokes read on the other layout: Thai text becomes Latin, anything else becomes Thai. */
export function retypeOnOtherLayout(text: string): string {
  const table = THAI_SCRIPT.test(text) ? toLatin : toThai;
  return Array.from(text, (char) => table.get(char) ?? char).join("");
}

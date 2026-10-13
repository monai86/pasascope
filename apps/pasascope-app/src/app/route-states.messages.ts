import { defineMessages } from "@/i18n/messages";

export const routeStateMessages = defineMessages({
  en: {
    notFound: {
      title: "This page does not exist",
      description: "The address may be mistyped, or the page may have moved. Nothing was changed.",
      goToHome: "Go to home",
      goToCases: "Open Cases",
    },
    error: {
      title: "Something went wrong on this page",
      description: "The page could not be shown. Your saved work is not affected. Try again, or return to the home screen.",
      retry: "Try again",
      goToHome: "Go to home",
    },
  },
  th: {
    notFound: {
      title: "ไม่พบหน้านี้",
      description: "ที่อยู่อาจพิมพ์ผิด หรือหน้านี้ถูกย้ายไปแล้ว ไม่มีข้อมูลใดถูกเปลี่ยนแปลง",
      goToHome: "ไปหน้าหลัก",
      goToCases: "เปิดรายการเคส",
    },
    error: {
      title: "หน้านี้เกิดข้อผิดพลาด",
      description: "ไม่สามารถแสดงหน้านี้ได้ งานที่บันทึกไว้แล้วไม่ได้รับผลกระทบ ลองอีกครั้งหรือกลับไปหน้าหลัก",
      retry: "ลองอีกครั้ง",
      goToHome: "ไปหน้าหลัก",
    },
  },
});

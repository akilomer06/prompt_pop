import { BookOpen, Image as ImageIcon, WandSparkles } from "lucide-react";
export const roundNames = ["AI knowledge", "Image recreation", "Logo design"];
export const roundIcons = [BookOpen, ImageIcon, WandSparkles];
export const dateTime = (n: number) =>
  new Date(n * 1000).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
export const shortTime = (n: number) =>
  new Date(n * 1000).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
export const human = (s: string) => s.replaceAll("_", " ");

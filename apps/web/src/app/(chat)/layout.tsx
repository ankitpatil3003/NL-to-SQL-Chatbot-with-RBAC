import ChatShell from "@/components/ChatShell";

// Layouts stay mounted when navigating between their pages, so "/" and "/chat/[id]" share one
// ChatShell: a new chat moving to its own URL mid-answer keeps its stream. The pages themselves
// render nothing; ChatShell reads the chat id from the URL.
export default function ChatLayout({ children }: LayoutProps<"/">) {
  return (
    <>
      <ChatShell />
      {children}
    </>
  );
}

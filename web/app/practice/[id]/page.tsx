import { Chat } from "@/components/Chat"

export default function Practice({ params }: { params: { id: string } }) {
  return <Chat sessionId={params.id} />
}

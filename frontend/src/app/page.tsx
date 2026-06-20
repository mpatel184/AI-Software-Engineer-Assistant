import { redirect } from "next/navigation";

/** Entry point — auth-aware routing is added with the auth module (Step 5). */
export default function HomePage() {
  redirect("/dashboard");
}

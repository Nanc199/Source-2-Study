import { redirect } from 'next/navigation';

export default function VerifyEmailPage({ searchParams }: { searchParams: { token?: string } }) {
  const token = searchParams.token;
  if (!token) {
    redirect('/verify');
  }

  redirect(`/verify?token=${encodeURIComponent(token)}`);
}

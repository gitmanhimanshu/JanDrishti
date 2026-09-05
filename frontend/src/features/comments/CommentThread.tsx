'use client';

/**
 * Threaded discussion (spec 25).
 *
 * Reading is public and needs no account. Posting calls `requireAuth`, so an
 * anonymous reader can start typing, press Post, sign in, and have their
 * comment submitted — rather than losing what they wrote.
 */
import { useCallback, useEffect, useState } from 'react';

import { VerifiedProfessionalBadge } from '@/components/ui/StatusBadge';
import { useAuth } from '@/features/authentication/auth-context';
import { formatRelative } from '@/lib/format';
import { api } from '@/services/api-client';
import type { Comment } from '@/types/api';

const MAX_REPLY_DEPTH = 5;

interface ThreadResponse {
  count: number;
  comments: Comment[];
}

export function CommentThread({
  targetType,
  targetId,
}: {
  targetType: 'PROBLEM' | 'EXPERIENCE' | 'PROJECT';
  targetId: string;
}) {
  const [thread, setThread] = useState<ThreadResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const load = useCallback(async () => {
    setIsLoading(true);
    setLoadError(false);
    try {
      setThread(await api.get<ThreadResponse>(`/comments/${targetType}/${targetId}/`));
    } catch {
      setLoadError(true);
    } finally {
      setIsLoading(false);
    }
  }, [targetType, targetId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="mt-4">
      <CommentComposer targetType={targetType} targetId={targetId} onPosted={load} />

      {isLoading && (
        <p className="mt-6 text-sm text-ink-400" role="status">
          Loading discussion…
        </p>
      )}

      {loadError && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-sm text-red-800">The discussion could not be loaded.</p>
          <button
            type="button"
            onClick={() => void load()}
            className="mt-2 text-sm font-medium text-red-900 underline"
          >
            Try again
          </button>
        </div>
      )}

      {thread && !isLoading && (
        <>
          <p className="mt-6 text-sm text-ink-500">
            {thread.count === 0
              ? 'No comments yet.'
              : `${thread.count} comment${thread.count === 1 ? '' : 's'}`}
          </p>
          <div className="mt-4 space-y-5">
            {thread.comments.map((comment) => (
              <CommentNode
                key={comment.id}
                comment={comment}
                targetType={targetType}
                targetId={targetId}
                onPosted={load}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function CommentNode({
  comment,
  targetType,
  targetId,
  onPosted,
}: {
  comment: Comment;
  targetType: 'PROBLEM' | 'EXPERIENCE' | 'PROJECT';
  targetId: string;
  onPosted: () => Promise<void>;
}) {
  const [isReplying, setIsReplying] = useState(false);
  const canReply = comment.depth < MAX_REPLY_DEPTH;

  return (
    <div className={comment.depth > 0 ? 'border-l-2 border-ink-100 pl-4' : ''}>
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ink-100 text-xs font-semibold text-ink-700">
          {(comment.author?.display_name ?? '?').charAt(0).toUpperCase()}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="text-sm font-medium text-ink-900">
              {comment.author?.display_name ?? 'Removed account'}
            </span>
            <VerifiedProfessionalBadge badge={comment.author?.verification_badge ?? null} />
            <span className="text-xs text-ink-400">{formatRelative(comment.created_at)}</span>
          </div>

          <p className="mt-1 whitespace-pre-line text-sm leading-relaxed text-ink-700">
            {comment.body}
          </p>

          {canReply && (
            <button
              type="button"
              onClick={() => setIsReplying((open) => !open)}
              className="mt-1.5 text-xs font-medium text-ink-500 transition hover:text-brand-700"
            >
              {isReplying ? 'Cancel' : 'Reply'}
            </button>
          )}

          {isReplying && (
            <div className="mt-3">
              <CommentComposer
                targetType={targetType}
                targetId={targetId}
                parentId={comment.id}
                compact
                onPosted={async () => {
                  setIsReplying(false);
                  await onPosted();
                }}
              />
            </div>
          )}

          {comment.replies.length > 0 && (
            <div className="mt-4 space-y-4">
              {comment.replies.map((reply) => (
                <CommentNode
                  key={reply.id}
                  comment={reply}
                  targetType={targetType}
                  targetId={targetId}
                  onPosted={onPosted}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function CommentComposer({
  targetType,
  targetId,
  parentId,
  compact = false,
  onPosted,
}: {
  targetType: 'PROBLEM' | 'EXPERIENCE' | 'PROJECT';
  targetId: string;
  parentId?: string;
  compact?: boolean;
  onPosted: () => Promise<void>;
}) {
  const { requireAuth, isAuthenticated } = useAuth();
  const [body, setBody] = useState('');
  const [isPosting, setIsPosting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const post = useCallback(async () => {
    const text = body.trim();
    if (!text) return;
    setIsPosting(true);
    setError(null);
    try {
      await api.post('/comments/', {
        target_type: targetType,
        target_id: targetId,
        body: text,
        ...(parentId ? { parent_id: parentId } : {}),
      });
      setBody('');
      await onPosted();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Your comment could not be posted.');
    } finally {
      setIsPosting(false);
    }
  }, [body, onPosted, parentId, targetId, targetType]);

  const submit = () =>
    requireAuth(post, {
      label: parentId ? 'Login to reply' : 'Login to comment',
      returnPath: typeof window === 'undefined' ? '/' : window.location.pathname,
    });

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <label htmlFor={`comment-${parentId ?? 'root'}`} className="sr-only">
        {parentId ? 'Write a reply' : 'Write a comment'}
      </label>
      <textarea
        id={`comment-${parentId ?? 'root'}`}
        value={body}
        onChange={(event) => setBody(event.target.value)}
        rows={compact ? 2 : 3}
        maxLength={4000}
        placeholder={
          parentId
            ? 'Write a reply…'
            : 'Add what you know: when it started, how it affects people, what has been tried.'
        }
        className="w-full rounded-lg border border-ink-300 px-3 py-2.5 text-sm placeholder:text-ink-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
      />

      {error && (
        <p role="alert" className="mt-1.5 text-xs text-red-700">
          {error}
        </p>
      )}

      <div className="mt-2 flex items-center justify-between gap-3">
        <p className="text-xs text-ink-400">
          {isAuthenticated
            ? `${body.length}/4000`
            : 'You can write now — we will ask you to sign in when you post.'}
        </p>
        <button
          type="submit"
          disabled={isPosting || body.trim().length === 0}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50"
        >
          {isPosting ? 'Posting…' : parentId ? 'Reply' : 'Post comment'}
        </button>
      </div>
    </form>
  );
}

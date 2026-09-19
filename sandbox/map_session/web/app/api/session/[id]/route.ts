import { QUERY_STATE, errorResponse, temporal } from "@/lib/temporal";
import type { SessionState } from "@/lib/types";

/** Current session state. The map polls this. */
export async function GET(_req: Request, ctx: RouteContext<"/api/session/[id]">) {
  const { id } = await ctx.params;
  try {
    const client = await temporal();
    const state = await client.workflow.getHandle(id).query<SessionState>(QUERY_STATE);
    return Response.json(state);
  } catch (err) {
    return errorResponse(err);
  }
}

import { TASK_QUEUE, WORKFLOW, errorResponse, temporal } from "@/lib/temporal";
import type { AssessmentInput } from "@/lib/types";

/** Start a session: one AssessWorkflow run. Returns its id, which is the session id. */
export async function POST(req: Request) {
  const input = (await req.json()) as AssessmentInput;
  const id = `assess-${crypto.randomUUID().slice(0, 8)}`;
  try {
    const client = await temporal();
    await client.workflow.start(WORKFLOW, { taskQueue: TASK_QUEUE, workflowId: id, args: [input] });
    return Response.json({ id });
  } catch (err) {
    return errorResponse(err);
  }
}

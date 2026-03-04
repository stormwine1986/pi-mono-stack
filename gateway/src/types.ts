export interface WorkerTask {
    id?: string;
    user_id?: string;
    source?: string;
    prompt?: string;
    images?: string[]; // Relative paths to images in workspace (e.g. ".gateway/abc.jpg")
    [key: string]: any;
}

export type WorkerResponse = {
    id?: string;
    user_id?: string;
    source?: string;
    agent_id?: string;
} & (
        | { status: "success"; response: string; images?: string[] }
        | { status: "error"; error: string }
        | { status: "progress"; event: "llm_start" | "llm_end" | "tool_start" | "tool_end" | "send_media"; data?: any }
    );

export interface WorkerControlSignal {
    id?: string;
    user_id?: string;
    source?: string;
    command: "stop" | "steer" | "reset";
    message?: string;
}

export type User = {
  id: string;
  username: string;
  role: "admin" | "participant" | "judge";
  team_id: string | null;
  team_name?: string;
};
export type Criterion = { name: string; weight: number };
export type Task = {
  id: number;
  round: number;
  title: string;
  brief?: string;
  requirements?: string;
  duration: number;
  grace: number;
  attempt_limit: number;
  status: string;
  deadline: number | null;
  remaining: number | null;
  rubric: Criterion[];
  reference_id?: string;
};
export type EventState = {
  title: string;
  current: number;
  published: boolean;
  weights: number[];
  tie_break: string;
  integrity_threshold: number;
  quiz_question_count: number;
  server_time: number;
  offset: number;
  tasks: Task[];
  integration: {
    session_capture: boolean;
    attempt_tracking: boolean;
    evaluator_configured: boolean;
    reason: string;
  };
};
export type Team = {
  id: string;
  name: string;
  members: string[];
  username: string;
  active: boolean;
  online: boolean;
  submissions: number;
  late: number;
  answers: number;
  incidents: number;
};
export type Submission = {
  id: string;
  team_id: string;
  task_id: number;
  prompt: string;
  link: string;
  rationale: string;
  asset_id: string;
  evidence_id: string | null;
  submitted: number;
  revision: number;
  receipt: string;
  status: string;
  late: boolean;
  evidence_flag: boolean;
  scores: number[] | null;
  notes: string;
  approved: boolean;
};
export type Ranking = {
  rank: number;
  team_id: string;
  team: string;
  rounds: number[];
  total: number;
};

export type Confirmation = {
  title: string;
  description: string;
  label: string;
  action: () => Promise<void>;
  danger?: boolean;
};
export type Common = {
  state: EventState;
  notify: (s: string) => void;
  refresh: () => void;
  confirm: (c: Confirmation) => void;
};

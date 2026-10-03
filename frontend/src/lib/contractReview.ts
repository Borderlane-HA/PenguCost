// Descriptive edits save directly. Review only changes that affect costs or term.
const numericFields=['amount','interval_months','minimum_term_months','renewal_period_months','renewal_amount'];
const termFields=['currency','billing_interval','start_date','contract_end','auto_renew','status','recurrence_type'];
const numeric=(value:unknown)=>value==null||value===''?null:Number(value);
const value=(input:unknown)=>input==null||input===''?null:input;
export function contractChangeNeedsReview(before:Record<string,any>,after:Record<string,any>):boolean{
 if(numericFields.some(key=>numeric(before[key])!==numeric(after[key])))return true;
 if(termFields.some(key=>value(before[key])!==value(after[key])))return true;
 return (before.recurrence_type==='one_time'||after.recurrence_type==='one_time')&&value(before.next_due_date)!==value(after.next_due_date);
}

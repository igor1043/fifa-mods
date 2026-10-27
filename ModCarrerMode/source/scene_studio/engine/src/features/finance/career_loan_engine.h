#ifndef CAREER_LOAN_ENGINE_H
#define CAREER_LOAN_ENGINE_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

/* Money is integral native save units, never floats or salary/baseline fields.
 * This module owns no file handles and cannot write a save on its own. */
typedef struct CareerLoanTerms {
    uint32_t principal, interest_basis_points, installments;
    uint32_t contract_date, first_due_date, interval_months;
} CareerLoanTerms;
typedef struct CareerLoanSchedule {
    uint32_t total, installment_base, extra_unit_installments;
    uint32_t due_dates[120], amounts[120], count;
} CareerLoanSchedule;
typedef struct CareerLoanSnapshot {
    uint32_t club, manager, date, setup_date, transfer_budget, wage_budget, currency;
    size_t budget_bit, budget_crc_start, budget_crc_offset;
    uint32_t original_crc;
} CareerLoanSnapshot;

int career_loan_schedule(const CareerLoanTerms*, CareerLoanSchedule*);
/* Only the unpaid installments which have reached their due dates. The caller
 * must persist paid_count transactionally; reloading a screen is not a payment. */
int career_loan_due(const CareerLoanSchedule*, uint32_t today, uint32_t paid_count,
    uint32_t* due_count, uint32_t* due_amount);
int career_loan_read_save(const void*,size_t,CareerLoanSnapshot*,char*,size_t);
/* In-memory, atomic on rejection, exact dqXv.SnDr bits plus table/container CRCs.
 * Requires the original snapshot to match, preventing stale UI money writes. */
int career_loan_patch_budget(void*,size_t,const CareerLoanSnapshot*,int64_t delta,
    CareerLoanSnapshot*,char*,size_t);
#ifdef __cplusplus
}
#endif
#endif

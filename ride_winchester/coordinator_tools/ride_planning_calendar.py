"""

Create the planning claendar fo RW co-ordinator

"""

from datetime import datetime
from dateutil.relativedelta import relativedelta

from tabulate import tabulate


def generate_monthly_block_dates(start_date_str, num_blocks):
    """Generate key dates for ride planning calendar over a series of 2-month blocks"""

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    results = []

    for i in range(num_blocks):
        # Calculate the start of the current 2-month block
        # relativedelta handles the math of jumping exactly 2 calendar months
        block_start = start_date + relativedelta(months=2 * i)
        block_end = block_start + relativedelta(months=2) - relativedelta(days=1)

        # Calculate target dates relative to the block start

        block_number = i + 1

        results.append(
            {
                "Block": f"{block_number}",
                "Block Start": block_start.strftime("%Y-%m-%d"),
                "Block End": block_end.strftime("%Y-%m-%d"),
                "dates": [
                    {
                        "Who": "RW Coordinator",
                        "Action": "Email the schedule and links to Ride Coordinators",
                        "Due date": (block_start - relativedelta(days=25)).strftime("%Y-%m-%d"),
                    },
                    {
                        "Who": "RW Coordinator",
                        "Action": "Email links and deadlines to ride leaders",
                        "Due date": (block_start - relativedelta(days=24)).strftime("%Y-%m-%d"),
                    },
                    {
                        "Who": "Secretary",
                        "Action": "Send reminder email to leaders",
                        "Due date": (block_start - relativedelta(days=19)).strftime("%Y-%m-%d"),
                    },
                    {
                        "Who": "Ride Leaders",
                        "Action": "Ride Leader offers deadline",
                        "Due date": (block_start - relativedelta(days=17)).strftime("%Y-%m-%d"),
                    },
                    {
                        "Who": "RW Coordinator",
                        "Action": "Run auto-selection and email results to ride co-ordinators",
                        "Due date": (block_start - relativedelta(days=16)).strftime("%Y-%m-%d"),
                    },
                    {
                        "Who": "Ride Coordinators",
                        "Action": "Deadline for manual changes/edits",
                        "Due date": (block_start - relativedelta(days=11)).strftime("%Y-%m-%d"),
                    },
                    {
                        "Who": "RW Coordinator",
                        "Action": "Email Leaders. Upload programme to RW & website",
                        "Due date": (block_start - relativedelta(days=10)).strftime("%Y-%m-%d"),
                    },
                ]
            }
        )

    return results


def main():
    """Entry point"""
    first_block_start = "2025-10-01"
    number_of_blocks = 6

    data = generate_monthly_block_dates(first_block_start, number_of_blocks)

    # Simple display
    for row in data:
        print(f"Ride recruitment schedule for: {row['Block Start']} to {row['Block End']}")
        print()
        print(tabulate(row['dates'], headers="keys"))
        print()


if __name__ == "__main__":
    main()

# Step 0: Load Required Libraries
if (!require("pdftools")) install.packages("pdftools", repos = "https://cran.rstudio.com/")
if (!require("dplyr")) install.packages("dplyr", repos = "https://cran.rstudio.com/")
if (!require("stringr")) install.packages("stringr", repos = "https://cran.rstudio.com/")

library(pdftools)
library(dplyr)
library(stringr)

# Step 1: Define the path to the PDF file and read the entire PDF content
pdf_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/Loch_Lomond_spill_record.pdf"  # Update this path if needed

# Read the entire PDF content as text (all pages)
pdf_text_all <- pdf_text(pdf_path)

# Combine text from all pages into a single string for easier processing
combined_text <- paste(pdf_text_all, collapse = "\n")

# Step 2: Split the combined text into individual lines
lines <- str_split(combined_text, "\n")[[1]]

# Step 3: Clean and Extract Table Data
clean_lines <- function(lines) {
  # Remove empty lines and trim whitespace
  lines <- lines[lines != ""]
  lines <- trimws(lines)
  
  # Filter lines that represent table data (those starting with a year)
  table_lines <- lines[grep("^[0-9]{4}", lines)]
  return(table_lines)
}

# Clean the lines to get only the table data
table_data <- clean_lines(lines)

# Display the cleaned table data for verification
print(table_data)

# Step 4: Extract Columns and Create the Data Frame
# Split the cleaned table data using whitespace as a delimiter
extracted_data <- str_split_fixed(table_data, "\\s{2,}", 5)

# Create a data frame with the appropriate columns
spill_record <- data.frame(
  Year = extracted_data[, 1],
  Spill = extracted_data[, 2],
  `End of Spill` = extracted_data[, 3],
  `Second Spill` = extracted_data[, 4],
  `Second End of Spill` = extracted_data[, 5],
  stringsAsFactors = FALSE
)

# Step 5: Replace empty strings in the data frame with NA values
spill_record[spill_record == ""] <- NA

# Step 6: Display the final structured data frame
print(spill_record)

# Step 7: Save the extracted data to a CSV file for easy loading in VSCode or further processing
output_path <- "/data/muscat_data/jaguir26/project1_ucsc_phd/Loch_Lomond_spill_record.csv"
write.csv(spill_record, file = output_path, row.names = FALSE)

# Confirm saving the file
cat("Data saved successfully to:", output_path)

use serde::{Deserialize, Serialize};

// WarData Struct, representa los datos de una guerra
#[derive(Serialize, Deserialize, Debug)]
pub struct WarData {
      country: String,
      warplanes_in_air: u32,
      warships_in_water: u32,
      timestamp: String,
}
    
# Cleanup / Archive Candidates (No Deletions Performed)

## Large data and outputs
| Path | Size | Reason | Safe action |
| --- | --- | --- | --- |
| `prism_data/` | 55G | Raw PRISM download cache; re-downloadable | Move to `data_raw/` and add to `.gitignore` |
| `frames/` | 6.6G | Likely GIF/animation frames | Move to `outputs/` or `archive/` |
| `Project/` | 6.1G | External workspace used by download scripts | Move to `archive/` or relocate outside repo |
| `DISC_variables_*_exAL_synth_DISC.RData` | 7.1G each | Derived model outputs | Move to `outputs/model/` and gitignore |
| `DISC_variables_50_NDLM_synth_DISC.RData` | 6.0G | Derived model output | Move to `outputs/model/` and gitignore |
| `variables_*_exAL_synth_DISC_uni.RData` | 3.8G each | Derived model outputs | Move to `outputs/model/` and gitignore |
| `PCA_variables_*_exAL_synth_PCA.RData` | 3.6G each | Derived PCA outputs | Move to `outputs/model/` and gitignore |

## Toolchains, SDKs, and local builds
| Path | Size | Reason | Safe action |
| --- | --- | --- | --- |
| `cmake-3.22.1/` | 1.8G | Local toolchain build | Archive or delete if unused |
| `boost_1_81_0/`, `boost_1_82_0/` | 1.3G each | Local Boost source/build | Archive or delete if unused |
| `eccodes-2.26.0-Source/` | 527M | Local build tree | Archive or delete if unused |
| `google-cloud-sdk/` | 763M | SDK install | Archive or delete if unused |
| `julia-1.9.3/` | 501M | Julia install | Archive or delete if unused |
| `icu/` | 419M | Local ICU build | Archive or delete if unused |
| `aws/` | 257M | AWS CLI/SDK install | Archive or delete if unused |
| `imcmc_env/` | 193M | Local env folder | Archive or delete if unused |
| `R-4.3.1/`, `lapack/`, `fftw-3.3.10/`, `nlopt-2.7.0/`, `rclone-v1.67.0-linux-amd64/` | 9.5M-117M | Local installs/builds | Archive or delete if unused |

## Installer archives
| Path | Size | Reason | Safe action |
| --- | --- | --- | --- |
| `boost_1_81_0.tar.gz`, `boost_1_82_0.tar.gz`, `cmake-3.22.1.tar.gz`, `eccodes-2.26.0-Source.tar.gz`, `julia-1.9.3-linux-x86_64.tar.gz`, `R-4.3.1.tar.gz` | varies | Installer tarballs | Delete after confirming installs |
| `awscliv2.zip`, `google-cloud-sdk-438.0.0-linux-x86_64.tar.gz`, `Miniconda3-latest-Linux-x86_64.sh`, `ngrok-v3-stable-linux-amd64.tgz` | varies | Installer archives | Delete after confirming installs |

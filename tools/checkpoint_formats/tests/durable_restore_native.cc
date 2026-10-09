#include "../durable_restore.h"
#include <fstream>
#include <iostream>
int main(int argc,char **argv) {
  if(argc!=3) return 2;
  try {
    const auto text=read_durable_restore(argv[1]);
    std::ofstream output(argv[2],std::ios::binary); output<<text; output.close();
    if(!output) return 2;
    std::cout<<"ACCEPT complete_image=1\n"; return 0;
  } catch(const std::exception &error) {
    std::cout<<"REJECT no_publication=1 "<<error.what()<<'\n'; return 1;
  }
}

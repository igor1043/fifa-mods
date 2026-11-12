#include "manager_face_model.h"
#include <cassert>
int main(){
 std::vector<managerface::Choice> rows;
 std::istringstream good("1043\tCOACH-TITE\tTite\tminifaces/tite.png\n1\tCOACH-CENI\tCeni\tminifaces/ceni.png\n");
 assert(managerface::load(good,rows)&&rows.size()==3&&rows[0].asset==0&&rows[1].asset==1043);
 std::istringstream windows("1043\tCOACH-TITE\tTite\tminifaces/tite.png\r\n1\tCOACH-CENI\tCeni\tminifaces/ceni.png\r\n");
 assert(managerface::load(windows,rows)&&rows[1].image=="minifaces/tite.png"&&rows[2].image=="minifaces/ceni.png");
 std::vector<managerface::Choice> clubs;
 std::istringstream affiliated("517\tCOACH-TITE\tTite\tminifaces/tite.png\t0\tSem clube\r\n383\tCOACH-ABEL\tAbel Ferreira\tminifaces/abel.png\t383\tPalmeiras\r\n");
 assert(managerface::load(affiliated,clubs)&&clubs[1].club==0&&clubs[2].club==383&&clubs[2].clubName=="Palmeiras");
 for(const char* value:{"1\tCOACH-X\tX\tminifaces/../../bad.png\n","1\tCOACH-X\tX\tC:/bad.png\n","0\tCOACH-X\tX\tminifaces/x.png\n","1\tbad\tX\tminifaces/x.png\n","1\tCOACH-X\tX\tminifaces/x.png\n1\tCOACH-X\tX\tminifaces/x.png\n"}){
  std::istringstream bad(value);assert(!managerface::load(bad,rows));assert(rows.size()==3);
 }
 assert(managerface::step(5,1,37)==6&&managerface::step(5,-1,37)==4);
 assert(managerface::step(36,1,37)==36&&managerface::step(0,-1,37)==0);
 assert(managerface::firstVisible(7,0,37)==1&&managerface::firstVisible(0,5,37)==0);
 assert(managerface::firstVisible(36,0,37)==30);
 std::istringstream regional("383\tCOACH-ABEL\tAbel Ferreira\tminifaces/a.png\t383\tPalmeiras\t54\t54\t7\t1\tBrasil\tSérie A\n1\tCOACH-TITE\tTite\tminifaces/t.png\t1\tOutro\t54\t54\t83\t2\tBrasil\tSérie B\n2\tCOACH-X\tX\tminifaces/x.png\t2\tBarcelona\t45\t45\t53\t1\tEspanha\tLaLiga\n");
 assert(managerface::load(regional,rows));managerface::Filter filter;
 assert((filter.visible(rows)==std::vector<int>{1,2,3}));
 filter.grouped=true;filter.follow(rows,1);assert((filter.visible(rows)==std::vector<int>{1}));
 assert(filter.options(rows,0).size()==2&&filter.options(rows,1).size()==2);
 assert(filter.cycle(rows,1,1)==2&&filter.league==83);assert(filter.cycle(rows,1,-1)==1&&filter.league==7);
 assert(filter.cycle(rows,0,1)==3&&filter.country==45&&filter.league==53);
 filter.grouped=false;assert(filter.visible(rows).size()==3);
 assert(managerface::scrollFirst(10,0,14,5)==6&&managerface::scrollFirst(0,6,14,5)==0);
}
